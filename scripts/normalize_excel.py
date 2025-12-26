import argparse
from pathlib import Path
import pandas as pd


def flatten_headers(df: pd.DataFrame) -> pd.DataFrame:
    # MultiIndex columns -> DataFrame
    cols = pd.DataFrame(df.columns.tolist()).ffill()
    df.columns = [
        " | ".join([str(x).strip() for x in row if str(x) != "nan" and str(x).strip() != ""])
        for row in cols.values
    ]
    return df


def normalize_one_excel(path: Path, header_rows=(0, 1, 2)) -> pd.DataFrame:
    df = pd.read_excel(path, header=list(header_rows))

    df = flatten_headers(df)

    # ilk iki kolonu year/threshold varsayıyoruz (TÜİK tablolarında genelde böyle)
    df = df.rename(columns={
        df.columns[0]: "year",
        df.columns[1]: "threshold",
    })

    value_cols = [c for c in df.columns if c not in ("year", "threshold")]

    long = df.melt(
        id_vars=["year", "threshold"],
        value_vars=value_cols,
        var_name="metric_education",
        value_name="value",
    )

    # "metric | education" ayrıştır
    split = long["metric_education"].str.split(" | ", n=1, expand=True)
    long["metric"] = split[0]
    long["education"] = split[1] if split.shape[1] > 1 else None

    # düzen
    long["source_file"] = str(path)
    return long


def iter_excels(root: Path):
    exts = {".xls", ".xlsx"}
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            yield p


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="downloads klasörü veya alt klasörü (örn: downloads/yoksulluk)")
    parser.add_argument("--out", default="normalized", help="çıktı klasörü (default: normalized)")
    parser.add_argument("--header", default="0,1,2", help="header satırları (default: 0,1,2)")
    parser.add_argument("--limit", type=int, default=0, help="test için ilk N dosya (0=hepsi)")
    args = parser.parse_args()

    root = Path(args.root)
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    header_rows = tuple(int(x) for x in args.header.split(",") if x.strip() != "")

    files = list(iter_excels(root))
    if args.limit and args.limit > 0:
        files = files[:args.limit]

    print(f"[INFO] root={root} excel_count={len(files)} header={header_rows} out={out_root}")

    ok = 0
    fail = 0

    for i, fpath in enumerate(files, start=1):
        try:
            long = normalize_one_excel(fpath, header_rows=header_rows)

            # çıktı yolunu input’a göre aynala
            rel = fpath.relative_to(root)
            out_csv = (out_root / rel).with_suffix(".csv")
            out_csv.parent.mkdir(parents=True, exist_ok=True)

            long.to_csv(out_csv, index=False)
            ok += 1
            print(f"[{i:04d}] OK  -> {out_csv}")
        except Exception as e:
            fail += 1
            print(f"[{i:04d}] ERR -> {fpath}")
            print(f"       err: {e}")

    print(f"[DONE] ok={ok} fail={fail} out={out_root}")


if __name__ == "__main__":
    main()
