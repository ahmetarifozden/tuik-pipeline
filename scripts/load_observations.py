import argparse
from src.tuik_pipeline.etl.loader import run_loader_pipeline
from src.tuik_pipeline.core.logging import setup_logging

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("root")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    run_loader_pipeline(args.root, args.limit)
