import json

import requests

from .interface import GrASPEstimateResult, GrASPEstimator, GrASPQueryContext


class ExternalGrASPEstimator(GrASPEstimator):
    def __init__(self, endpoint: str, timeout_ms: int = 1500):
        self._endpoint = endpoint
        self._timeout_s = max(timeout_ms, 100) / 1000.0

    def estimate(self, ctx: GrASPQueryContext) -> GrASPEstimateResult:
        payload = {
            "query": ctx.query,
            "database": ctx.database,
            "schema": ctx.schema,
            "source": "dbtune",
            "interface_version": "0.1",
        }

        try:
            resp = requests.post(self._endpoint, json=payload, timeout=self._timeout_s)
            resp.raise_for_status()
        except requests.RequestException as exc:
            raise RuntimeError(f"external GrASP endpoint request failed: {exc}") from exc

        try:
            parsed = resp.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError("external GrASP endpoint did not return valid JSON") from exc

        return self._parse_response(parsed)

    def mode_name(self) -> str:
        return "external"

    def _parse_response(self, parsed: object) -> GrASPEstimateResult:
        if not isinstance(parsed, dict):
            raise RuntimeError("external GrASP response is not a JSON object")

        body = parsed.get("data", parsed)
        if not isinstance(body, dict):
            raise RuntimeError("external GrASP response body is invalid")

        prefetch_plan = self._read_prefetch_plan(body)
        confidence = self._read_confidence(body)
        model = self._read_model(body)

        return GrASPEstimateResult(
            prefetch_plan=prefetch_plan,
            confidence=confidence,
            model=model,
        )

    @staticmethod
    def _read_prefetch_plan(body: dict) -> list[str]:
        candidates = [
            body.get("prefetch_plan"),
            body.get("predicted_blocks"),
            body.get("recommended_blocks"),
            body.get("result"),
        ]
        for item in candidates:
            if isinstance(item, list) and all(isinstance(v, str) for v in item):
                return item
        raise RuntimeError("external GrASP response missing valid prefetch plan")

    @staticmethod
    def _read_confidence(body: dict) -> float:
        candidates = [body.get("confidence"), body.get("score")]
        for item in candidates:
            try:
                return float(item)
            except (TypeError, ValueError):
                continue
        return 0.5

    @staticmethod
    def _read_model(body: dict) -> str:
        model = body.get("model")
        if isinstance(model, str) and model:
            return model
        return "grasp-external-v0"
