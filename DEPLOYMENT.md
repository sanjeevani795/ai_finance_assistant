# Deployment runbook (secrets-free image)

This runbook describes how to run **ai_finance_assistant** in Docker **without baking API keys or `.env` into the image**. Secrets are always supplied at **runtime** by your shell, Compose, Kubernetes, or your cloud secret manager.

## Principles

1. **Image**: contains code, `config.yaml`, and sample `data/` text only. No `OPENAI_API_KEY`, no `.env`.
2. **Runtime**: inject `OPENAI_API_KEY` (required). Optionally inject `ALPHA_VANTAGE_API_KEY`.
3. **FAISS index**: optional on-disk directory under `data/faiss_index/`. If missing, the app still starts; RAG context is empty until you build an index (see below).
4. **Networking**: the container listens on `0.0.0.0:7860` by default. Override with `GRADIO_SERVER_NAME` / `GRADIO_SERVER_PORT` if needed.

## Prerequisites

- Docker 24+ and Docker Compose v2 (or compatible `docker compose`).
- An OpenAI API key available to the runtime environment (never committed to git).

## Option A — Docker Compose (recommended for demos)

From the `ai_finance_assistant` directory:

```bash
export OPENAI_API_KEY="sk-..."                 # required
export ALPHA_VANTAGE_API_KEY=""                # optional
export PUBLISH_PORT=7860                       # host port → container 7860

docker compose up --build
```

Open `http://localhost:${PUBLISH_PORT:-7860}`.

To load keys from a **local gitignored** file instead of your shell:

1. Copy `.env.example` to `.env`, fill in keys.
2. In `docker-compose.yml`, uncomment the `env_file: - .env` block under `app:`.

### Persist FAISS and logs

Uncomment the `volumes` block under `app:` in `docker-compose.yml`, then create / populate `data/faiss_index` on the host.

**Build the demo index once** (writes into the bind mount; uses your OpenAI key for embeddings):

```bash
export OPENAI_API_KEY="sk-..."
mkdir -p data/faiss_index
# Container runs as UID 1000; ensure the host directory is writable (example for local dev):
sudo chown -R 1000:1000 data/faiss_index
docker compose --profile ingest run --rm ingest
docker compose up --build
```

## Option B — `docker run`

Build:

```bash
docker build -t ai-finance-assistant:local .
```

Run (keys via environment, not files in the image):

```bash
docker run --rm \
  -e OPENAI_API_KEY="sk-..." \
  -e ALPHA_VANTAGE_API_KEY="" \
  -e GRADIO_SERVER_NAME=0.0.0.0 \
  -e GRADIO_SERVER_PORT=7860 \
  -p 7860:7860 \
  ai-finance-assistant:local
```

Optional bind mounts:

```bash
mkdir -p data/faiss_index logs
docker run --rm \
  -e OPENAI_API_KEY="sk-..." \
  -p 7860:7860 \
  -v "$(pwd)/data/faiss_index:/app/data/faiss_index" \
  -v "$(pwd)/logs:/app/logs" \
  ai-finance-assistant:local
```

## Option C — Kubernetes (sketch)

- Store `OPENAI_API_KEY` in a **Secret**; reference it as an env var on the Pod.
- Mount an **emptyDir** or **PVC** at `/app/data/faiss_index` if you want durable RAG; run a **Job** once to execute `python scripts/build_demo_index.py` with the same secret, writing into the volume, or build the index in CI and ship it as an artifact you mount read-only.
- Expose the Service on port `7860` (or put Gradio behind an Ingress / API gateway with TLS and auth).

Do **not** put raw keys in `ConfigMap` manifests.

## Health checks

The Dockerfile `HEALTHCHECK` curls `http://127.0.0.1:7860/`. If you change `GRADIO_SERVER_PORT`, update the Dockerfile health check or disable it in derived images.

## Production hardening (checklist)

- Put the UI **behind authentication** (reverse proxy, VPN, or IdP); Gradio is not a multi-tenant auth product by itself.
- Terminate **TLS** at the load balancer or ingress.
- Restrict **egress** if your policy requires allowlisting OpenAI / market APIs.
- Set **resource limits** (CPU/memory) on the container.
- Use **read-only root filesystem** where compatible; mount writable volumes only for `data/faiss_index` and `logs` if needed.
- Rotate API keys and audit access via your cloud provider.

## Troubleshooting

| Symptom | Likely cause |
|--------|----------------|
| Container exits immediately | `OPENAI_API_KEY` missing at runtime. |
| Empty RAG answers | No FAISS files under `/app/data/faiss_index`. Run `scripts/build_demo_index.py` or mount a populated directory. |
| Health check failing | Gradio not ready yet, or port mismatch. Increase `start-period` or align `GRADIO_SERVER_PORT` with `HEALTHCHECK`. |
| `Permission denied` writing FAISS | Bind-mounted `data/faiss_index` not writable by UID **1000** inside the image. `chown` on the host (see ingest example above). |

## Files reference

- `Dockerfile` — slim Python image, non-root user, no secrets.
- `scripts/docker_entrypoint.sh` — refuses to start without `OPENAI_API_KEY`.
- `docker-compose.yml` — local orchestration and optional `ingest` profile.
- `.dockerignore` — keeps `.env`, venvs, and build artifacts out of the build context.
