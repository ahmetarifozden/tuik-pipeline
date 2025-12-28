from sqlalchemy import String, Integer, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.tuik_pipeline.core.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Upper ID from Tuik categories
    ust_id: Mapped[int] = mapped_column(Integer, index=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publish_date_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)

    download_path: Mapped[str] = mapped_column(Text, nullable=False)
    download_url: Mapped[str] = mapped_column(Text, nullable=False)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint(
            "ust_id",
            "download_path",
            "title",
            name="uq_datasets_ust_path_title"
        ),
    )
