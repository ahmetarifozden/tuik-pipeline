import csv
import re
import pandas as pd
from pathlib import Path

from src.tuik_pipeline.core.logging import get_logger

logger = get_logger(__name__)

def safe_dirname(text: str, max_len: int = 80) -> str:
    text = (text or "").strip().lower()
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^0-9a-zA-ZğüşöçıİĞÜŞÖÇ_-]+", "", text)
    text = text[:max_len].strip("_")
    return text or "unknown"

def safe_filename(text: str, max_len: int = 200) -> str:
    text = (text or "").strip()
    text = re.sub(r"[\\/:*?\"<>|]+", "", text)
    text = re.sub(r"\s+", " ", text)
    text = text[:max_len].rstrip()
    return text or "untitled"

def is_excel(path: Path) -> bool:
    return path.suffix.lower() in (".xls", ".xlsx")

def flatten_columns(cols) -> list[str]:
    """
    Flattens MultiIndex columns into a single string.
    """
    out = []
    for c in cols:
        if isinstance(c, tuple):
            parts = [
                str(x).strip() 
                for x in c 
                if x is not None and str(x).strip() and str(x).strip().lower() != "nan"
            ]
            out.append(" | ".join(parts) if parts else "col")
        else:
            s = str(c).strip()
            out.append(s if s else "col")
    return out

def normalize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Basic normalization:
    - Flatten columns
    - Drop empty rows
    - Clean whitespace in object columns
    """
    df = df.copy()
    df.columns = flatten_columns(df.columns)

    # Drop completely empty rows
    df = df.dropna(how="all")

    # Clean whitespace in string columns
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    return df

def detect_year_column(df: pd.DataFrame) -> str | None:
    """
    Tries to identify a 'Year' column.
    """
    candidates = []
    for c in df.columns:
        cl = c.lower()
        if "yıl" in cl or "year" in cl:
            candidates.append(c)
    return candidates[0] if candidates else None

def melt_to_observation_format(df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms wide format to long format:
    year | threshold | metric | education | value
    """
    df = df.copy()

    year_col = detect_year_column(df)
    if not year_col:
        return df

    # Standardize year column name
    df = df.rename(columns={year_col: "year"})

    id_vars = ["year"]
    value_vars = [c for c in df.columns if c not in id_vars]

    long_df = df.melt(id_vars=id_vars, value_vars=value_vars, var_name="dimension", value_name="value")

    # Heuristic decomposition of dimension string
    long_df["metric"] = long_df["dimension"]
    long_df["education"] = None
    long_df["threshold"] = None

    # Return only relevant columns if they exist
    cols = ["year", "threshold", "metric", "education", "value"]
    # Ensure they exist (fill None if not)
    for c in cols:
        if c not in long_df.columns:
            long_df[c] = None
    
    return long_df[cols]

def run_normalization_pipeline(
    manifest_path_str: str, 
    out_root_str: str = "normalized",
    header_rows: list[int] = [0, 1, 2],
    limit: int = 0
):
    manifest_path = Path(manifest_path_str)
    out_root = Path(out_root_str)

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    # Read manifest
    rows = []
    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if limit > 0:
        rows = rows[:limit]

    logger.info(f"Processing {len(rows)} items from manifest: {manifest_path}")

    ok_count = 0
    fail_count = 0

    for i, r in enumerate(rows, start=1):
        try:
            dataset_id = int(r["dataset_id"])
            keyword = r.get("keyword") or ""
            group_name = r.get("group_name") or ""
            title = r.get("title") or ""
            saved_path = Path(r["saved_path"])

            if not saved_path.exists():
                logger.warning(f"File missing: {saved_path}")
                continue

            if not is_excel(saved_path):
                logger.debug(f"Skipping non-excel: {saved_path.name}")
                continue

            # Output paths
            kw_dir = out_root / safe_dirname(keyword)
            # Normalized Group Directory
            grp_dir = kw_dir / safe_dirname(group_name)
            grp_dir.mkdir(parents=True, exist_ok=True)
            
            out_csv = grp_dir / (safe_filename(title) + ".csv")

            # Read Excel
            df = pd.read_excel(saved_path, header=header_rows)
            df = normalize_dataframe(df)
            long_df = melt_to_observation_format(df)

            # Enriched metadata
            long_df["dataset_id"] = dataset_id
            long_df["keyword"] = keyword
            long_df["group_name"] = group_name
            long_df["title"] = title
            long_df["source_file"] = str(saved_path)

            long_df.to_csv(out_csv, index=False)
            ok_count += 1
            logger.info(f"[{i:04d}] OK -> {out_csv}")

        except Exception as e:
            fail_count += 1
            logger.error(f"Failed to normalize item {i}: {e}")

    logger.info(f"Normalization Complete. OK={ok_count} FAIL={fail_count}")
