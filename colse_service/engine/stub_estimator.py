from .interface import CardinalityEstimator


class StubCoLSEEstimator(CardinalityEstimator):
    def estimate(self, normalized_query: str) -> float:
        # Deterministic fallback estimate for integration testing.
        return float(max(1, len(normalized_query)))

