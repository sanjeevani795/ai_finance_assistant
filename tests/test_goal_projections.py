from agents.goal_projections import future_value_lump_sum, goal_projection_block, payment_for_future_value


def test_future_value_lump_sum() -> None:
    fv = future_value_lump_sum(1000.0, 0.07, 10)
    assert fv > 1900


def test_payment_for_future_value_positive() -> None:
    pmt = payment_for_future_value(100_000.0, 0.06, 20, pv=10_000.0, periods_per_year=12)
    assert pmt > 0


def test_goal_projection_block_requires_numbers() -> None:
    assert goal_projection_block("How should I think about goals?") == ""
