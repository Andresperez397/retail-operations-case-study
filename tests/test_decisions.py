"""Decision logic on small hand-built tables."""

from __future__ import annotations

import pandas as pd
import pytest

from retail import cancellations
from retail import range as r


def test_abc_classes_start_rule_and_non_positive_last():
    net = pd.Series({"a": 70.0, "b": 15.0, "c": 9.0, "d": 4.0, "e": 2.0, "f": 0.0, "g": -3.0})
    cls = r.abc_classes(net)
    # Shares start at 0, .70, .85, .94, .98: the product that crosses 80% (b) is still A.
    assert cls.to_dict() == {"a": "A", "b": "A", "c": "B", "d": "B", "e": "C", "f": "C", "g": "C"}


def product_year():
    rows = []
    spec = {  # code: (Y1 net, Y1 orders, first sale, Y2 net, Y2 lines)
        "A1": (900, 50, "2010-01-01", 800, 40),
        "C1": (5, 3, "2010-01-01", 0, 0),
        "C2": (4, 1, "2010-02-01", 300, 30),  # grows in year 2: a false cut
        "C3": (1, 2, "2010-10-01", 10, 2),  # new launch
        "C4": (3, 5, "2010-03-01", 5, 1),
    }
    for code, (n1, o1, first, n2, l2) in spec.items():
        rows.append(dict(stock_code=code, analysis_year="Y1", net_revenue=n1, sale_lines=o1, orders=o1,
                         first_sale=pd.Timestamp(first), description=code))  # fmt: skip
        rows.append(dict(stock_code=code, analysis_year="Y2", net_revenue=n2, sale_lines=l2, orders=l2,
                         first_sale=pd.NaT, description=code))  # fmt: skip
    return pd.DataFrame(rows)


def test_cut_rules():
    py = product_year()
    key = pd.Series({"C2": 3, "C4": 1})
    y1 = r.year1_frame(py, key, a=0.80, b=0.95)
    cuts = r.cut_lists(y1)
    assert cuts["R1"] == ["C1", "C2", "C4"]  # class C minus the new launch C3
    assert cuts["R2"] == ["C1", "C2", "C3", "C4"]
    assert len(cuts["R3"]) == len(cuts["R1"]) and "C3" not in cuts["R3"]
    assert cuts["R4"] == ["C1", "C4"]  # C2 has 3 key-account buyers


def test_year2_measures():
    py = product_year()
    y2 = py[py["analysis_year"] == "Y2"].set_index("stock_code")
    pairs = pd.DataFrame({"stock_code": ["A1", "C2", "C2", "C4"], "customer_id": ["x", "x", "y", "z"]})
    m = r.year2_measures(["C1", "C2", "C4"], y2, pairs)
    assert m["M1_revenue_at_risk"] == pytest.approx(305 / 1115)
    assert m["M2_share_still_selling"] == pytest.approx(2 / 3)
    assert m["M3_false_cuts"] == 1  # C2 is year-2 class A or B
    assert m["M5_share_of_customers_touched"] == pytest.approx(1.0)


def test_bootstrap_is_reproducible_and_brackets_estimate():
    lines = pd.DataFrame({
        "stock_code": ["A1", "C2", "A1", "C4", "A1", "C2"],
        "customer_id": ["x", "x", "y", None, "z", "z"],
        "invoice": ["1", "1", "2", "3", "4", "4"],
        "line_value": [100.0, 20.0, 80.0, 5.0, 60.0, 10.0],
    })  # fmt: skip
    cuts = {"R1": ["C2", "C4"], "R2": ["C2"], "R3": ["C4"], "R4": []}
    a = r.cluster_bootstrap(lines, cuts, reps=200)
    b = r.cluster_bootstrap(lines, cuts, reps=200)
    assert a == b
    assert a["clusters"] == 4  # three customers plus one invoice without an ID
    lo, hi = a["R1_M1_ci"]
    assert lo <= 35 / 275 <= hi


def test_cancellation_persistence():
    py = []
    for i in range(60):
        rate = 0.3 if i < 5 else 0.01
        for yr in ("Y1", "Y2"):
            py.append(dict(stock_code=f"P{i:02d}", analysis_year=yr, sale_lines=100, cancel_lines=int(100 * rate)))
    py.append(dict(stock_code="SMALL", analysis_year="Y1", sale_lines=5, cancel_lines=5))
    w = cancellations.eligible_rates(pd.DataFrame(py))
    assert "SMALL" not in w.index and len(w) == 60
    out = cancellations.persistence(w, watch_size=5, reps=50)
    assert set(out["watch_list"]) == {f"P{i:02d}" for i in range(5)}
    assert out["ratio_Y2"] == pytest.approx(30.0)
