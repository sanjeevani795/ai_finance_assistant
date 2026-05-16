"""Finance Q&A specialist — primary consumer of RAG (personal finance & investing education)."""

from __future__ import annotations

from typing import ClassVar

from agents.base import BaseAgent


class FinanceQAAgent(BaseAgent):
    agent_id: ClassVar[str] = "finance_qa"

    def system_instruction(self) -> str:
        return (
            "You are the Finance Q&A specialist in a financial education assistant. "
            "You are not a licensed advisor.\n\n"
            "Use the RAG context when it is present: cite themes accurately and do not invent sources. "
            "If RAG is empty, explain general principles and state that you are not citing a specific corpus.\n"
            "Cover budgeting, credit, banking basics, investing terminology, and risk/return concepts at a high level."
        )
