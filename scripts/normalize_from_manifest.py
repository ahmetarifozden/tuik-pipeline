import argparse
import csv
import re
from pathlib import Path
import pandas as pd


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


def parse_header_list(vals: list[str]) -> list[int]:
    # ör: ["0","1","2"] -> [0,1,2]
    return [int(v) for v in vals]


def is_excel(path: Path) -> bool:
    return path.suffix.lower() in (".xls", ".xlsx")


def flatten_columns(cols) -> list[str]:
    """
    MultiIndex kolonları tek stringe çevirir.
    """
    out = []
    for c in cols:
        if isinstance(c, tuple):
            parts = [str(x).strip() for x in c if x is not None and str(x).strip() and str(x).strip().lower() != "nan"]
            out.append(" | ".join(parts) if parts else "col")
        else:
            s = str(c).strip()
            out.append(s if s else "col")
    return out


def normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Çok genel bir normalize:
    - Kolonları string yap
    - Tamamen boş satırları at
    - 'year' benzeri kolon bulup standardize etmeye çalış
    """
    df = df.copy()
    df.columns = flatten_columns(df.columns)

    # tamamen boş satırlar
    df = df.dropna(how="all")

    # satır başlıklarında newline vs temizle
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

    return df


def detect_year_column(df: pd.DataFrame) -> str | None:
    """
    'Yıllar', 'Years' geçen bir kolonu year olarak yakalamaya çalışır.
    """
    candidates = []
    for c in df.columns:
        cl = c.lower()
        if "yıl" in cl or "year" in cl:
            candidates.append(c)
    return candidates[0] if candidates else None


def melt_to_observation_like(df: pd.DataFrame) -> pd.DataFrame:
    """
    Observation tablosuna yakın uzun format üretmeye çalışır:
    year | threshold | metric | education | value
    Bu kısım dataset'lere göre değişebilir; burada minimum çalışan bir yaklaşım var.
    """
    df = df.copy()

    year_col = detect_year_column(df)
    if not year_col:
        # year yoksa olduğu gibi döndür, loader daha sonra özel ele alabilir
        return df

    # year kolonunu sabitle
    df = df.rename(columns={year_col: "year"})

    # year olmayan kolonları value olarak melt et
    id_vars = ["year"]
    value_vars = [c for c in df.columns if c not in id_vars]

    long = df.melt(id_vars=id_vars, value_vars=value_vars, var_name="dimension", value_name="value")

    # dimension'u parçalamaya çalış (heuristic)
    # ör: "Yoksulluk oranı (%) | Lise altı" gibi
    long["metric"] = long["dimension"]
    long["education"] = None
    long["threshold"] = None

    return long[["year", "threshold", "metric", "education", "value"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest", help="downloads/<kw>/manifest.csv yolu")
    ap.add_argument("--out", default="normalized", help="çıktı kök klasörü")
    ap.add_argument("--header", nargs="+", default=["0", "1", "2"], help="read_excel header satırları (örn: 0 1 2)")
    ap.add_argument("--limit", type=int, default=0, help="test için ilk N dosya (0=hepsi)")
    args = ap.parse_args()

    manifest_path = Path(args.manifest)
    out_root = Path(args.out)
    header = parse_header_list(args.header)

    if not manifest_path.exists():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")

    rows = []
    with manifest_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    if args.limit and args.limit > 0:
        rows = rows[:args.limit]

    print(f"[INFO] manifest={manifest_path} rows={len(rows)} header={tuple(header)} out={out_root}")

    ok = 0
    fail = 0

    for i, r in enumerate(rows, start=1):
        try:
            dataset_id = int(r["dataset_id"])
            keyword = r.get("keyword") or ""
            group_name = r.get("group_name") or ""
            title = r.get("title") or ""
            saved_path = Path(r["saved_path"])

            if not saved_path.exists():
                raise FileNotFoundError(f"saved_path missing: {saved_path}")

            if not is_excel(saved_path):
                print(f"[{i:04d}] SKIP (not excel) -> {saved_path.name}")
                continue

            # output path
            kw_dir = out_root / safe_dirname(keyword)
            grp_dir = kw_dir / safe_dirname(group_name)
            grp_dir.mkdir(parents=True, exist_ok=True)
            out_csv = grp_dir / (safe_filename(title) + ".csv")

            # Excel oku
            df = pd.read_excel(saved_path, header=header)

            df = normalize_df(df)
            long = melt_to_observation_like(df)

            # metadata kolonları ekle (EN ÖNEMLİ KISIM)
            long["dataset_id"] = dataset_id
            long["keyword"] = keyword
            long["group_name"] = group_name
            long["title"] = title
            long["source_file"] = str(saved_path)

            # yaz
            long.to_csv(out_csv, index=False)
            ok += 1
            print(f"[{i:04d}] OK  -> {out_csv}")

        except Exception as e:
            fail += 1
            print(f"[{i:04d}] ERR -> {r.get('saved_path')}")
            print(f"       err: {e}")

    print(f"[DONE] ok={ok} fail={fail} out={out_root}")


if __name__ == "__main__":
    main()
