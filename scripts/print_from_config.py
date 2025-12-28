import argparse
import sys
from src.tuik_pipeline.etl.downloader import run_downloader_pipeline
from src.tuik_pipeline.core.logging import setup_logging

if __name__ == "__main__":
    setup_logging()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("keyword", nargs="?", help="Search keyword")
    parser.add_argument("--config", default="config/crawl.yaml")
    parser.add_argument("--no-download-prompt", action="store_true")
    
    args = parser.parse_args()

    # If --no-download-prompt is passed, we skip prompt (True).
    run_downloader_pipeline(
        keyword_arg=args.keyword,
        config_path=args.config,
        skip_prompt=args.no_download_prompt
    )
