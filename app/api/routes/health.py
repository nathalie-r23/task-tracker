"""Health check route.

Exposes GET /health so clients (and you, via curl or Swagger) can
confirm the service is up.
"""

from datetime import datetime, timezone

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Return service status and the current UTC timestamp.

    A liveness check only: it confirms the process is up and serving, and does
    not inspect storage or any dependency. There are none — storage is
    in-process.

    Returns:
        A `HealthResponse` with `status` fixed to `"ok"` and `timestamp` as an
        ISO-8601 UTC string. The route answers 200.

    Example:
        curl http://localhost:8000/health
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )