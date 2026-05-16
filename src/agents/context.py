"""Shared context passed into every specialist agent run."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.config import AppConfig


@dataclass(frozen=True)
class AgentContext:
    """Immutable per-invocation inputs (orchestrator + prepare_context outputs)."""

    agent_id: str
    user_query: str
    conversation_context: str
    rag_context: str
    market_context: str
    user_profile_json: str
    cfg: "AppConfig"
