from __future__ import annotations

import pytest

from retail.scenario import Assumptions, economics

RULE = {"products_cut": 100, "M1_revenue_at_risk_usd": 10_000.0, "M4_share_of_sale_lines": 0.05}


def test_economics_arithmetic():
    e = economics(RULE, 200_000, Assumptions(gross_margin=0.4, cost_per_pick=0.5, cost_per_listing_year=20))
    assert e["gross_margin_lost"] == pytest.approx(4_000)
    assert e["pick_cost_saved"] == pytest.approx(0.05 * 200_000 * 0.5)  # 5,000
    assert e["listing_cost_saved"] == pytest.approx(2_000)
    assert e["net_benefit"] == pytest.approx(5_000 + 2_000 - 4_000)


def test_break_even_listing_cost_makes_net_benefit_zero():
    a = Assumptions(gross_margin=0.6, cost_per_pick=0.1)
    be = economics(RULE, 200_000, a)["break_even_cost_per_listing"]
    assert be > 0
    zero = economics(RULE, 200_000, Assumptions(0.6, 0.1, be))
    assert zero["net_benefit"] == pytest.approx(0, abs=1e-6)


def test_break_even_is_zero_when_picks_alone_pay_for_the_cut():
    assert economics(RULE, 1_000_000, Assumptions(0.1, 2.0))["break_even_cost_per_listing"] == 0.0
