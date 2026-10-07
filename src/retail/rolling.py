"""Rolling-origin check: apply the same four cut rules at several cut-off dates, each using only earlier data.

For a cut-off date the training window is the 12 months before it (or all data before it, if less) and the test
window is the 6 months after it. The rules are exactly those of `retail.range`; only the dates change. A product is
a "new launch" if its first sale in the training window falls in the last 3 months of that window.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from retail import range as R

DATA_START = pd.Timestamp("2009-12-01")


@dataclass(frozen=True)
class Origin:
    cutoff: pd.Timestamp
    train_months: int = 12
    test_months: int = 6

    @property
    def train_start(self) -> pd.Timestamp:
        return max(DATA_START, self.cutoff - pd.DateOffset(months=self.train_months))

    @property
    def test_end(self) -> pd.Timestamp:
        return self.cutoff + pd.DateOffset(months=self.test_months)

    @property
    def new_launch_from(self) -> pd.Timestamp:
        return self.cutoff - pd.DateOffset(months=3)


def window_products(con, start, end) -> pd.DataFrame:
    return con.execute(
        """SELECT stock_code,
                  any_value(description ORDER BY invoice_ts DESC) FILTER (WHERE line_type = 'sale') AS description,
                  sum(line_value) AS net_revenue,
                  count(*) FILTER (WHERE line_type = 'sale') AS sale_lines,
                  count(DISTINCT invoice) FILTER (WHERE line_type = 'sale') AS orders,
                  count(DISTINCT customer_id) FILTER (WHERE line_type = 'sale') AS customers,
                  min(invoice_ts) FILTER (WHERE line_type = 'sale') AS first_sale
           FROM product_lines WHERE invoice_ts >= ? AND invoice_ts < ? GROUP BY 1 ORDER BY 1""",
        [start.to_pydatetime(), end.to_pydatetime()],
    ).fetchdf()


def key_accounts(con, start, end) -> pd.Series:
    """Distinct top-decile customers (by net revenue in the window) buying each product in the window."""
    cust = con.execute(
        """SELECT customer_id, sum(line_value) AS net FROM product_lines
           WHERE invoice_ts >= ? AND invoice_ts < ? AND customer_id IS NOT NULL
           GROUP BY 1 HAVING count(*) FILTER (WHERE line_type = 'sale') > 0""",
        [start.to_pydatetime(), end.to_pydatetime()],
    ).fetchdf()
    top = cust.sort_values(["net", "customer_id"], ascending=[False, True]).head(math.ceil(0.1 * len(cust)))
    pairs = con.execute(
        """SELECT DISTINCT stock_code, customer_id FROM product_lines
           WHERE invoice_ts >= ? AND invoice_ts < ? AND line_type = 'sale' AND customer_id IS NOT NULL""",
        [start.to_pydatetime(), end.to_pydatetime()],
    ).fetchdf()
    return pairs[pairs["customer_id"].isin(top["customer_id"])].groupby("stock_code")["customer_id"].nunique()


def evaluate(con, origin: Origin, boot_reps: int = 1000) -> dict:
    train = window_products(con, origin.train_start, origin.cutoff).assign(analysis_year="Y1")
    test = window_products(con, origin.cutoff, origin.test_end)
    ka = key_accounts(con, origin.train_start, origin.cutoff)
    y1 = R.year1_frame(train, ka, cutoff=origin.new_launch_from)
    cuts = R.cut_lists(y1)
    y2 = test.set_index("stock_code")
    pairs = con.execute(
        """SELECT DISTINCT stock_code, customer_id FROM product_lines
           WHERE invoice_ts >= ? AND invoice_ts < ? AND line_type = 'sale' AND customer_id IS NOT NULL""",
        [origin.cutoff.to_pydatetime(), origin.test_end.to_pydatetime()],
    ).fetchdf()
    lines = con.execute(
        """SELECT stock_code, customer_id, invoice, line_value FROM product_lines
           WHERE invoice_ts >= ? AND invoice_ts < ? ORDER BY row_id""",
        [origin.cutoff.to_pydatetime(), origin.test_end.to_pydatetime()],
    ).fetchdf()
    eligible = sorted(y1.index[~y1["new_launch"]])
    boot = R.cluster_bootstrap(lines, cuts, reps=boot_reps)
    return {
        "train": [str(origin.train_start.date()), str((origin.cutoff - pd.Timedelta(days=1)).date())],
        "test": [str(origin.cutoff.date()), str((origin.test_end - pd.Timedelta(days=1)).date())],
        "range_size": int(len(y1)),
        "measures": {r: R.year2_measures(c, y2, pairs) for r, c in cuts.items()},
        "M1_ci": {r: boot[f"{r}_M1_ci"] for r in cuts},
        "random_baseline_M1": R.random_baseline(eligible, len(cuts["R1"]), y2),
        "test_net_revenue_usd": float(y2["net_revenue"].sum()),
    }
