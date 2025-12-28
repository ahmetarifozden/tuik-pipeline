from sqlalchemy import (
    Column, Integer, BigInteger, String, ForeignKey,
    Numeric, DateTime, func, Index, Text
)
from src.tuik_pipeline.core.database import Base


class Observation(Base):
    __tablename__ = "observations"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Link to datasets table (reference only, cascading delete)
    dataset_id = Column(Integer, ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False, index=True)

    year = Column(Integer, nullable=True, index=True)
    threshold = Column(Text, nullable=True)   # e.g., "%50"
    metric = Column(Text, nullable=False, index=True)
    education = Column(Text, nullable=True, index=True)

    value = Column(Numeric(18, 6), nullable=True)

    source_file = Column(Text, nullable=True) # normalized csv path or excel path
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        # Index to check uniqueness if needed
        # Index("uq_obs", "dataset_id", "year", "threshold", "metric", "education", unique=True),
        Index("ix_obs_dataset_year", "dataset_id", "year"),
    )
