"""Goal planning — SMART-style coaching plus deterministic projection snippets when numbers are parseable."""

from __future__ import annotations

from typing import ClassVar

from agents.base import BaseAgent
from agents.context import AgentContext
from agents.goal_projections import goal_projection_block


class GoalPlanningAgent(BaseAgent):
    agent_id: ClassVar[str] = "goal_planning"

    def system_instruction(self) -> str:
        return (
            "You are the Goal Planning specialist. Help users frame goals (specific, measurable, time-bound), "
            "discuss savings tradeoffs, and interpret the deterministic projection snippets when provided. "
            "Clearly label projections as simplified (no taxes/fees) and ask for missing numbers before "
            "over-confident estimates."
        )

    def extra_llm_blocks(self, ctx: AgentContext) -> str:
        return goal_projection_block(ctx.user_query)
