"""Re-apply the four cut rules at three more cut-off dates (see DEVIATIONS.md item 10).

PYTHONPATH=src python scripts/run_rolling.py
"""

from __future__ import annotations

import json

import pandas as pd

from retail import rolling
from retail.db import ROOT, staged

ORIGINS = [pd.Timestamp("2010-06-01"), pd.Timestamp("2010-12-01"), pd.Timestamp("2011-06-01")]


def main() -> None:
    con = staged()
    out = {}
    for cutoff in ORIGINS:
        out[str(cutoff.date())] = rolling.evaluate(con, rolling.Origin(cutoff))
    # The stated expectations (DEVIATIONS.md item 10), checked mechanically.
    checks = {
        "R4_below_R1_every_origin": all(
            v["measures"]["R4"]["M1_revenue_at_risk"] < v["measures"]["R1"]["M1_revenue_at_risk"] for v in out.values()
        ),
        "R2_above_R1_every_origin": all(
            v["measures"]["R2"]["M1_revenue_at_risk"] > v["measures"]["R1"]["M1_revenue_at_risk"] for v in out.values()
        ),
        "R4_under_3pct_every_origin": all(v["measures"]["R4"]["M1_revenue_at_risk"] <= 0.03 for v in out.values()),
    }
    (ROOT / "reports" / "tables" / "rolling_origins.json").write_text(
        json.dumps({"origins": out, "checks": checks}, indent=2)
    )
    for k, v in out.items():
        m = v["measures"]
        print(k, v["train"], v["test"], {r: round(100 * m[r]["M1_revenue_at_risk"], 2) for r in m},
              "random", round(100 * v["random_baseline_M1"]["median"], 1))  # fmt: skip
    print(checks)


if __name__ == "__main__":
    main()
