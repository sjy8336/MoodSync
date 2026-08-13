from pydantic import BaseModel


class DatabaseHealthResponse(BaseModel):
    connected: bool
    message: str

