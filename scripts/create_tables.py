from app.core.db import Base, engine

# modelleri import etmezsen Base onları bilmez
from app.models.dataset import Dataset  # noqa: F401

def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

if __name__ == "__main__":
    main()
