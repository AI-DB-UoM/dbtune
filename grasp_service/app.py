from fastapi import FastAPI, HTTPException

from adapters import normalize_sql
from engine import build_estimator
from engine.interface import GrASPQueryContext
from schemas import (
    GrASPEstimateRequest,
    GrASPEstimateResponse,
    GrASPProtocolResponse,
    GrASPServiceInfoResponse,
)

app = FastAPI(title="GrASP Service", version="0.1.1-dev")
estimator = build_estimator()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/grasp/info", response_model=GrASPServiceInfoResponse)
def info() -> GrASPServiceInfoResponse:
    return GrASPServiceInfoResponse(mode=estimator.mode_name())


@app.get("/grasp/protocol", response_model=GrASPProtocolResponse)
def protocol() -> GrASPProtocolResponse:
    return GrASPProtocolResponse(
        request_fields=["query", "database", "schema", "source", "interface_version"],
        response_fields=["status", "model", "prefetch_plan", "confidence"],
        compatibility_fields=[
            "data.prefetch_plan",
            "predicted_blocks",
            "recommended_blocks",
            "result",
            "score",
        ],
    )


@app.post("/grasp/estimate", response_model=GrASPEstimateResponse)
def estimate(req: GrASPEstimateRequest) -> GrASPEstimateResponse:
    normalized = normalize_sql(req.query)
    if not normalized:
        raise HTTPException(status_code=400, detail="query is required")

    try:
        result = estimator.estimate(
            GrASPQueryContext(
                query=normalized,
                database=req.database,
                schema=req.schema,
            )
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return GrASPEstimateResponse(
        status="ok",
        model=result.model,
        normalized_query=normalized,
        prefetch_plan=result.prefetch_plan,
        confidence=result.confidence,
        mode=estimator.mode_name(),
    )
