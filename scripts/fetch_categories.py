from pathlib import Path
import sys
from src.tuik_pipeline.etl.extractors import update_categories_yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT_FILE = PROJECT_ROOT / "config" / "categories.yaml"

if __name__ == "__main__":
    sys.exit(update_categories_yaml(OUT_FILE))
