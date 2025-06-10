from pydantic import BaseModel
from typing import List, Optional, Any

class MABRequest(BaseModel):
    table: str
    columns: List[str]
    options: Optional[dict] = {}

class MABResponse(BaseModel):
    status: str
    suggestion: str
    query: Optional[str] = None
    config: Optional[Any] = None
