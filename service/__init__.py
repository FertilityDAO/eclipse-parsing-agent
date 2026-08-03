"""Production Fingerprint Service.

Request-time replacement for docs/product/prototype/build_fixtures.py. Same
payload, computed per request from the frozen engine instead of baked for five
hardcoded places.

    from service.contracts import FingerprintRequest
    from service.pipeline import run
"""
from .contracts import FingerprintRequest, FingerprintResponse  # noqa: F401
from .pipeline import PipelineIncomplete, run, status  # noqa: F401

__all__ = ["FingerprintRequest", "FingerprintResponse", "PipelineIncomplete",
           "run", "status"]
