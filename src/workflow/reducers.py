"""LangGraph state reducers."""

from __future__ import annotations

RESET_AGENT_OUTPUTS = "__reset__"


def merge_agent_outputs(
    left: dict[str, str] | None,
    right: dict[str, str] | None,
) -> dict[str, str]:
    """Merge parallel specialist dict updates; support clearing stale checkpoint data."""
    acc = dict(left or {})
    upd = dict(right or {})
    if RESET_AGENT_OUTPUTS in upd:
        acc.clear()
        upd = {k: v for k, v in upd.items() if k != RESET_AGENT_OUTPUTS}
    acc.update(upd)
    return acc
