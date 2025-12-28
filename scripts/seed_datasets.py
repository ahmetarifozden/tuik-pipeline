from pathlib import Path
from src.tuik_pipeline.etl.extractors import seed_datasets
from src.tuik_pipeline.core.logging import setup_logging

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CATEGORIES_YAML = PROJECT_ROOT / "config" / "categories.yaml"

if __name__ == "__main__":
    setup_logging()
    seed_datasets(CATEGORIES_YAML)
