from pydantic import BaseModel


class IngestionResponse(BaseModel):
    code: int
    message: str
    task_ids: list[str]