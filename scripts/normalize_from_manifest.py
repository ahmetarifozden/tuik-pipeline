import argparse
from src.tuik_pipeline.etl.normalizer import run_normalization_pipeline
from src.tuik_pipeline.core.logging import setup_logging

if __name__ == "__main__":
    setup_logging()
    
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--out", default="normalized")
    ap.add_argument("--header", nargs="+", default=["0", "1", "2"])
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    header_rows = [int(x) for x in args.header]

    run_normalization_pipeline(
        manifest_path_str=args.manifest,
        out_root_str=args.out,
        header_rows=header_rows,
        limit=args.limit
    )
