# --- Runtime image: no API keys or .env baked in. Provide secrets via orchestrator / compose. ---
FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY config.yaml run.py README.md ./
COPY data ./data
COPY scripts ./scripts
COPY src ./src

RUN chmod +x /app/scripts/docker_entrypoint.sh \
    && mkdir -p /app/data/faiss_index /app/logs \
    && chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860

EXPOSE 7860

# Gradio serves HTTP on server_port; adjust if you change GRADIO_SERVER_PORT.
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD curl -fsS "http://127.0.0.1:7860/" >/dev/null || exit 1

ENTRYPOINT ["/app/scripts/docker_entrypoint.sh"]
CMD ["python", "run.py"]
