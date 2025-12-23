# scripts/init_db.py
from app.core.db import Base, engine

# Modeller import edilmezse SQLAlchemy Base'e kayıt olmaz ve tablo oluşmaz.
from app.models import category, dataset, run, value  # noqa: F401

def main():
    Base.metadata.create_all(bind=engine)
    print("[OK] create_all done")

if __name__ == "__main__":
    main()
