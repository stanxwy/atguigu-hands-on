from pydantic import BaseModel, Field


class TaskStatusResponse(BaseModel):
    status: str = Field(..., description="task status")
    done_list: list[str] = Field(..., description="list of nodes done")
    running_list: list[str] = Field(..., description="list of nodes running")