# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
# Dependencies are resolved here so that pip, its wheel cache and any transient
# build tooling never reach the final image.
FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# A self-contained virtualenv means the runtime stage can take the whole
# dependency tree in a single COPY.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /build

COPY requirements.txt .
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Non-root user. Created before anything is copied in so the app never owns
# the interpreter or its dependencies — only its own source.
RUN useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# Only the ASGI package. Tests, docs, the frontend, .env and git metadata are
# all excluded (see .dockerignore): the API mounts no static files, so
# frontend/ is not a runtime dependency.
COPY --chown=app:app app ./app

USER app

EXPOSE 8000

# No --reload: the watcher is a development convenience and would restart the
# container's only process on any file event.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
