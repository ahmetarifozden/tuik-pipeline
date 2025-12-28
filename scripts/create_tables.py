from src.tuik_pipeline.core.database import Base, engine
# Import models to register them
from src.tuik_pipeline.models import Category, Dataset, Observation

def main():
    print("[INFO] Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("[OK] Tables created successfully.")

if __name__ == "__main__":
    main()
