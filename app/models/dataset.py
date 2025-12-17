from sqlalchemy import String, Integer, Text, Boolean, Date, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class Dataset(Base):
    __tablename__ = "datasets"
    __table_args__ = (
        UniqueConstraint("download_path", name="uq_datasets_download_path"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    ust_id: Mapped[int] = mapped_column(Integer, index=True)
    group_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    publish_date_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)

    download_path: Mapped[str] = mapped_column(Text, nullable=False)
    download_url: Mapped[str] = mapped_column(Text, nullable=False)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
