"""Pydantic models for the health endpoint."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Shape of the GET /health response body."""

    status: str
    timestamp: str
