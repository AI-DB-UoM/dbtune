from .interface import GrASPEstimateResult, GrASPEstimator, GrASPQueryContext


class StubGrASPEstimator(GrASPEstimator):
    def estimate(self, ctx: GrASPQueryContext) -> GrASPEstimateResult:
        tokens = ctx.query.lower().split()
        if "where" in tokens:
            return GrASPEstimateResult(
                prefetch_plan=["sequential_prefetch", "predicate_prefetch"],
                confidence=0.78,
                model="grasp-stub-v0",
            )
        return GrASPEstimateResult(
            prefetch_plan=["sequential_prefetch"],
            confidence=0.55,
            model="grasp-stub-v0",
        )

    def mode_name(self) -> str:
        return "stub"
