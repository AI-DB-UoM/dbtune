from pydantic import BaseModel, Field


class CoLSEEstimateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    database: str | None = None
    schema: str | None = None


class CoLSEEstimateResponse(BaseModel):
    status: str
    cardinality_estimate: float
    model: str
    normalized_query: str | None = None
