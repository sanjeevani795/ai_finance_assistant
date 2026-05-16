"""Tax education — concepts and account types; uses RAG when available and user profile JSON."""

from __future__ import annotations

from typing import ClassVar

from agents.base import BaseAgent


class TaxEducationAgent(BaseAgent):
    agent_id: ClassVar[str] = "tax_education"

    def system_instruction(self) -> str:
        return (
            "You are the Tax Education specialist. Explain concepts (marginal vs effective rates, capital gains "
            "basics, 401k vs IRA vs Roth, withholding) using RAG when present.\n"
            "Use the user profile JSON only for coarse context (e.g. country). Do not provide individualized filing "
            "or audit advice; encourage a qualified CPA/EA for complex situations."
        )
