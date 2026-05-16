"""Structured user context (e.g. passed into Tax Education / Goal Planning)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    display_name: Optional[str] = None
    country: str = "US"
    state_region: Optional[str] = None
    tax_filing_status: Optional[str] = Field(
        default=None,
        description="Optional; used only for generic education, not filing advice.",
    )
    risk_tolerance: Optional[str] = Field(default=None, description="low | medium | high")
    notes: Optional[str] = Field(default=None, description="Free-form preferences or constraints.")
