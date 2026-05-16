#!/bin/sh
# Entrypoint: fail fast if required runtime secrets are missing (image stays secret-free).
set -eu

if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "error: OPENAI_API_KEY is not set."
  echo "This image does not embed secrets. Pass OPENAI_API_KEY at runtime (docker run -e, compose env_file, or your orchestrator)."
  exit 1
fi

exec "$@"
