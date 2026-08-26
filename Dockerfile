# Non-root Python image for free-tier hosts (Render, Fly.io) and Kubernetes.
FROM python:3.12-slim

# Run as an unprivileged user — required by many platform security policies.
RUN useradd --create-home --uid 65532 appuser

WORKDIR /app

# Install dependencies before copying app code for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Writable path for SQLite on read-only root filesystems.
ENV DATA_DIR=/data
RUN mkdir -p /data && chown appuser:appuser /data

USER appuser

ENV PORT=8080
EXPOSE 8080

# Uvicorn serves the FastAPI app; host 0.0.0.0 binds all interfaces in containers.
CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]
