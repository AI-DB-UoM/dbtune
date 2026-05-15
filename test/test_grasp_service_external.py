import json
import pathlib
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "grasp_service"))

from engine.external_estimator import ExternalGrASPEstimator
from engine.interface import GrASPQueryContext


class _TestHandler(BaseHTTPRequestHandler):
    response_payload = {}

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        _ = self.rfile.read(content_length)

        body = json.dumps(self.response_payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


def _serve(payload: dict):
    _TestHandler.response_payload = payload
    server = HTTPServer(("127.0.0.1", 0), _TestHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server, thread


def test_external_estimator_parses_canonical_payload():
    payload = {
        "status": "ok",
        "model": "grasp-real-v1",
        "prefetch_plan": ["p1", "p2"],
        "confidence": 0.9,
    }
    server, thread = _serve(payload)
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}/grasp/estimate"
        estimator = ExternalGrASPEstimator(endpoint, timeout_ms=1500)
        result = estimator.estimate(GrASPQueryContext(query="select 1"))
        assert result.model == "grasp-real-v1"
        assert result.prefetch_plan == ["p1", "p2"]
        assert result.confidence == 0.9
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_external_estimator_parses_compatibility_payload():
    payload = {
        "data": {
            "model": "grasp-legacy",
            "recommended_blocks": ["block_a", "block_b"],
            "score": "0.63",
        }
    }
    server, thread = _serve(payload)
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}/predict"
        estimator = ExternalGrASPEstimator(endpoint, timeout_ms=1500)
        result = estimator.estimate(GrASPQueryContext(query="select * from t"))
        assert result.model == "grasp-legacy"
        assert result.prefetch_plan == ["block_a", "block_b"]
        assert result.confidence == 0.63
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_external_estimator_rejects_invalid_payload():
    payload = {"status": "ok", "confidence": 0.1}
    server, thread = _serve(payload)
    try:
        endpoint = f"http://127.0.0.1:{server.server_port}/predict"
        estimator = ExternalGrASPEstimator(endpoint, timeout_ms=1500)
        with pytest.raises(RuntimeError):
            estimator.estimate(GrASPQueryContext(query="select * from t"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
