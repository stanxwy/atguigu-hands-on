from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., description="user query")
    session_id: str = Field(None, description="session id for query")
    is_stream: bool = Field(False, description="whether use stream mode")

class QueryResponse(BaseModel):
    message: str
    session_id: str
    answer: str

class StreamSubmitResponse(BaseModel):
    message: str
    session_id: str
    task_id: str