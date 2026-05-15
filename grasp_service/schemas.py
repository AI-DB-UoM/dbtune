from pydantic import BaseModel, Field


class GrASPEstimateRequest(BaseModel):
    query: str = Field(..., min_length=1)
    database: str | None = None
    schema: str | None = None


class GrASPEstimateResponse(BaseModel):
    status: str
    model: str
    normalized_query: str | None = None
    prefetch_plan: list[str]
    confidence: float
    mode: str


class GrASPServiceInfoResponse(BaseModel):
    mode: str


class GrASPProtocolResponse(BaseModel):
    request_fields: list[str]
    response_fields: list[str]
    compatibility_fields: list[str]
