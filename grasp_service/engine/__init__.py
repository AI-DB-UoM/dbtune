from settings import GRASP_EXTERNAL_ENDPOINT, GRASP_MODE, GRASP_TIMEOUT_MS

from .external_estimator import ExternalGrASPEstimator
from .interface import GrASPEstimator
from .stub_estimator import StubGrASPEstimator


VALID_MODES = {"auto", "stub", "external"}


def build_estimator() -> GrASPEstimator:
    mode = GRASP_MODE if GRASP_MODE in VALID_MODES else "auto"

    if mode == "stub":
        return StubGrASPEstimator()

    if mode == "external":
        if not GRASP_EXTERNAL_ENDPOINT:
            raise RuntimeError(
                "GRASP_MODE is set to external but GRASP_EXTERNAL_ENDPOINT is empty"
            )
        return ExternalGrASPEstimator(GRASP_EXTERNAL_ENDPOINT, GRASP_TIMEOUT_MS)

    if GRASP_EXTERNAL_ENDPOINT:
        return ExternalGrASPEstimator(GRASP_EXTERNAL_ENDPOINT, GRASP_TIMEOUT_MS)

    return StubGrASPEstimator()
