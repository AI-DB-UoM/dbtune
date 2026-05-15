from dataclasses import dataclass
from typing import Protocol


@dataclass
class GrASPQueryContext:
    query: str
    database: str | None = None
    schema: str | None = None


@dataclass
class GrASPEstimateResult:
    prefetch_plan: list[str]
    confidence: float
    model: str


class GrASPEstimator(Protocol):
    def estimate(self, ctx: GrASPQueryContext) -> GrASPEstimateResult:
        ...

    def mode_name(self) -> str:
        ...
