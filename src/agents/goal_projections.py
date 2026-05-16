"""Small deterministic savings / goal projection helpers (FV, PMT-style)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_RATE_PAT = re.compile(r"(?:rate|apr|return)\s*(?:of|is|=|:)?\s*(\d+(?:\.\d+)?)\s*%?", re.I)
_YEARS_PAT = re.compile(r"(?:years?|yrs?|horizon)\s*(?:of|is|=|:)?\s*(\d+(?:\.\d+)?)", re.I)
_PV_PAT = re.compile(r"(?:present|starting|initial|have|saved)\s*(?:value|amount)?\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I)
_PMT_PAT = re.compile(r"(?:save|deposit|contribute)\s*\$?\s*([\d,]+(?:\.\d+)?)\s*(?:per|\/)\s*(month|year)", re.I)
_GOAL_PAT = re.compile(r"(?:goal|target|need)\s*\$?\s*([\d,]+(?:\.\d+)?)", re.I)


def _num(s: str) -> float:
    return float(s.replace(",", ""))


def future_value_lump_sum(pv: float, rate_annual: float, years: float) -> float:
    """FV of a single deposit: PV * (1+r)^n."""
    if years < 0 or rate_annual < -0.999:
        raise ValueError("Invalid inputs.")
    return pv * (1.0 + rate_annual) ** years


def future_value_annuity_due(
    payment: float,
    rate_annual: float,
    years: float,
    periods_per_year: int = 12,
) -> float:
    """FV of end-of-period contributions (ordinary annuity)."""
    if periods_per_year < 1:
        raise ValueError("periods_per_year must be >= 1")
    n = int(years * periods_per_year)
    r = rate_annual / periods_per_year
    if n <= 0:
        return 0.0
    if abs(r) < 1e-12:
        return payment * n
    return payment * ((1.0 + r) ** n - 1.0) / r


def payment_for_future_value(
    fv: float,
    rate_annual: float,
    years: float,
    pv: float = 0.0,
    periods_per_year: int = 12,
) -> float:
    """Periodic payment (end of period) to reach `fv` starting from `pv`."""
    n = max(1, int(years * periods_per_year))
    r = rate_annual / periods_per_year
    fv_from_pv = future_value_lump_sum(pv, rate_annual, years)
    need = fv - fv_from_pv
    if abs(r) < 1e-12:
        return need / n
    factor = ((1.0 + r) ** n - 1.0) / r
    if abs(factor) < 1e-12:
        raise ValueError("Cannot solve payment for these parameters.")
    return need / factor


@dataclass
class ParsedGoalNumbers:
    rate_annual: float | None
    years: float | None
    pv: float | None
    payment: float | None
    payment_period: str | None
    goal: float | None


def parse_goal_numbers(text: str) -> ParsedGoalNumbers:
    """Best-effort parse from natural language (no NLP)."""
    t = text or ""
    rate = None
    if (m := _RATE_PAT.search(t)):
        rate = _num(m.group(1)) / 100.0
    years = None
    if (m := _YEARS_PAT.search(t)):
        years = float(m.group(1))
    pv = None
    if (m := _PV_PAT.search(t)):
        pv = _num(m.group(1))
    pmt = None
    pmt_per = None
    if (m := _PMT_PAT.search(t)):
        pmt = _num(m.group(1))
        pmt_per = m.group(2).lower()
    goal = None
    if (m := _GOAL_PAT.search(t)):
        goal = _num(m.group(1))
    return ParsedGoalNumbers(rate, years, pv, pmt, pmt_per, goal)


def goal_projection_block(user_query: str) -> str:
    """Deterministic lines appended for the Goal Planning agent."""
    p = parse_goal_numbers(user_query)
    lines: list[str] = []
    if p.rate_annual is not None and p.years is not None and p.pv is not None:
        fv = future_value_lump_sum(p.pv, p.rate_annual, p.years)
        lines.append(
            f"Projected future value of lump sum: PV={p.pv:.2f}, r={p.rate_annual:.4f}/yr, "
            f"n={p.years:.2f}y → FV≈{fv:.2f} (compounded annually; educational)."
        )
    if (
        p.rate_annual is not None
        and p.years is not None
        and p.payment is not None
        and p.payment_period == "month"
    ):
        fv_ann = future_value_annuity_due(p.payment, p.rate_annual, p.years, 12)
        lines.append(
            f"Projected FV of monthly savings: ${p.payment:.2f}/mo for {p.years:.2f}y at "
            f"{p.rate_annual:.2%}/yr (monthly compounding, end-of-month) → ≈${fv_ann:.2f}."
        )
    if (
        p.goal is not None
        and p.rate_annual is not None
        and p.years is not None
        and p.pv is not None
    ):
        try:
            pay = payment_for_future_value(p.goal, p.rate_annual, p.years, pv=p.pv, periods_per_year=12)
            lines.append(
                f"Approx. monthly contribution needed to reach goal ${p.goal:.2f} from PV ${p.pv:.2f} "
                f"in {p.years:.2f}y at {p.rate_annual:.2%}/yr (monthly, end-of-month, no taxes): ≈${pay:.2f}/mo."
            )
        except Exception:
            pass
    if not lines:
        return ""
    return "Deterministic projection snippets (verify inputs; not tax or fee advice):\n" + "\n".join(lines)
