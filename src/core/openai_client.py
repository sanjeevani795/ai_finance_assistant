"""Thin OpenAI chat helpers (JSON + plain text)."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from core.config import AppConfig, require_openai_key

logger = logging.getLogger(__name__)


def get_client() -> OpenAI:
    return OpenAI(api_key=require_openai_key())


def chat_json(
    client: OpenAI,
    *,
    cfg: AppConfig,
    system: str,
    user: str,
    temperature: float | None = None,
) -> dict[str, Any]:
    temp = cfg.openai_temperature if temperature is None else temperature
    resp = client.chat.completions.create(
        model=cfg.openai_chat_model,
        temperature=temp,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON from model: %s", raw[:500])
        raise


def chat_text(
    client: OpenAI,
    *,
    cfg: AppConfig,
    system: str,
    user: str,
    temperature: float | None = None,
) -> str:
    temp = cfg.openai_temperature if temperature is None else temperature
    resp = client.chat.completions.create(
        model=cfg.openai_chat_model,
        temperature=temp,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return (resp.choices[0].message.content or "").strip()
