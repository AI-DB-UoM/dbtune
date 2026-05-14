from abc import ABC, abstractmethod


class CardinalityEstimator(ABC):
    @abstractmethod
    def estimate(self, normalized_query: str) -> float:
        raise NotImplementedError
