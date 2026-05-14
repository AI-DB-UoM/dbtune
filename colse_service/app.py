from fastapi import FastAPI, HTTPException

from adapters import normalize_sql
from engine import build_estimator
from schemas import CoLSEEstimateRequest, CoLSEEstimateResponse

app = FastAPI(title="CoLSE Service", version="0.1.1-dev")
estimator = build_estimator()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/colse/estimate", response_model=CoLSEEstimateResponse)
def estimate(req: CoLSEEstimateRequest):
    normalized = normalize_sql(req.query)
    if not normalized:
        raise HTTPException(status_code=400, detail="query is required")

    card_est = estimator.estimate(normalized)
    return CoLSEEstimateResponse(
        status="ok",
        cardinality_estimate=card_est,
        model="colse-stub-v0",
        normalized_query=normalized,
    )
