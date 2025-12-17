from pydantic import BaseModel

class DatasetOut(BaseModel):
    id: int
    ust_id: int
    group_name: str | None
    title: str
    publish_date_raw: str | None
    download_url: str

    class Config:
        from_attributes = True
