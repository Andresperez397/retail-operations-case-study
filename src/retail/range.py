"""Decision 1: which products to cut, chosen on year 1 and measured on year 2 (see ANALYSIS_PLAN.md)."""

from __future__ import annotations

import numpy as np
import pandas as pd

NEW_LAUNCH_CUTOFF = pd.Timestamp("2010-09-01")


def abc_classes(net_revenue: pd.Series, a: float = 0.80, b: float = 0.95) -> pd.Series:
    """ABC class per product: A covers the first `a` of cumulative net revenue, B up to `b`, C the rest.

    A product belongs to the class in which its cumulative share *starts*, so the product that crosses 80% is A.
    Products with zero or negative revenue sort last and are always C.
    """
    order = net_revenue.sort_values(ascending=False, kind="mergesort")
    total = order.clip(lower=0).sum()
    start = (order.cumsum() - order) / total
    cls = np.where(start < a, "A", np.where(start < b, "B", "C"))
    cls = pd.Series(cls, index=order.index)
    cls[order <= 0] = "C"
    return cls.reindex(net_revenue.index)


def year1_frame(product_year: pd.DataFrame, key_accounts: pd.Series, cutoff=NEW_LAUNCH_CUTOFF, a=0.80, b=0.95):
    """One row per product in the year-1 range with its class, new-launch flag and key-account count."""
    y1 = product_year[(product_year["analysis_year"] == "Y1") & (product_year["sale_lines"] > 0)].set_index(
        "stock_code"
    )
    y1 = y1.assign(
        abc=abc_classes(y1["net_revenue"], a, b),
        new_launch=y1["first_sale"] >= cutoff,
        key_account_buyers=key_accounts.reindex(y1.index).fillna(0).astype(int),
    )
    return y1


def cut_lists(y1: pd.DataFrame) -> dict[str, list[str]]:
    """The four pre-specified rules. R3 matches R1's size, ranked by fewest year-1 orders (ties by code)."""
    eligible = y1[~y1["new_launch"]]
    r1 = eligible[eligible["abc"] == "C"]
    r2 = y1[y1["abc"] == "C"]
    r3 = eligible.reset_index().sort_values(["orders", "stock_code"]).head(len(r1))
    r4 = r1[r1["key_account_buyers"] < 3]
    return {
        "R1": sorted(r1.index),
        "R2": sorted(r2.index),
        "R3": sorted(r3["stock_code"]),
        "R4": sorted(r4.index),
    }


def year2_measures(cut: list[str], y2: pd.DataFrame, y2_customers_by_product: pd.DataFrame) -> dict:
    """M1-M5 for one cut list. `y2` is indexed by stock_code; the customer frame has (stock_code, customer_id)."""
    total_net = y2["net_revenue"].sum()
    in_cut = y2.index.isin(cut)
    y2_abc = abc_classes(y2.loc[y2["sale_lines"] > 0, "net_revenue"])
    customers = y2_customers_by_product
    return {
        "products_cut": len(cut),
        "M1_revenue_at_risk": float(y2.loc[in_cut, "net_revenue"].sum() / total_net),
        "M1_revenue_at_risk_gbp": float(y2.loc[in_cut, "net_revenue"].sum()),
        "M2_share_still_selling": float((y2.loc[in_cut, "sale_lines"] > 0).sum() / len(cut)) if cut else 0.0,
        "M3_false_cuts": int(y2_abc.reindex(cut).isin(["A", "B"]).sum()),
        "M4_share_of_sale_lines": float(y2.loc[in_cut, "sale_lines"].sum() / y2["sale_lines"].sum()),
        "M5_share_of_customers_touched": float(
            customers.loc[customers["stock_code"].isin(cut), "customer_id"].nunique()
            / customers["customer_id"].nunique()
        ),
    }


def random_baseline(eligible: list[str], size: int, y2: pd.DataFrame, draws: int = 1000, seed: int = 2026) -> dict:
    rng = np.random.default_rng(seed)
    net = y2["net_revenue"].reindex(eligible).fillna(0).to_numpy()
    total = y2["net_revenue"].sum()
    shares = np.array([net[rng.choice(len(eligible), size, replace=False)].sum() / total for _ in range(draws)])
    return {
        "median": float(np.median(shares)),
        "p2_5": float(np.percentile(shares, 2.5)),
        "p97_5": float(np.percentile(shares, 97.5)),
    }


def cluster_bootstrap(y2_lines: pd.DataFrame, cuts: dict[str, list[str]], reps: int = 1000, seed: int = 2026) -> dict:
    """95% intervals for M1 of each rule and for R2-R1, R3-R1, R4-R1, resampling year-2 customers.

    Lines without a customer ID are clustered by invoice. `y2_lines` holds stock_code, customer_id, invoice and
    line_value for year-2 product lines.
    """
    cluster = y2_lines["customer_id"].fillna("invoice:" + y2_lines["invoice"])
    codes, uniques = pd.factorize(cluster)
    n = len(uniques)
    total = np.bincount(codes, weights=y2_lines["line_value"].to_numpy(), minlength=n)
    by_rule = {
        r: np.bincount(codes, weights=(y2_lines["line_value"] * y2_lines["stock_code"].isin(c)).to_numpy(), minlength=n)
        for r, c in cuts.items()
    }
    rng = np.random.default_rng(seed)
    draws = {r: np.empty(reps) for r in cuts}
    for i in range(reps):
        w = np.bincount(rng.integers(0, n, n), minlength=n)
        t = w @ total
        for r, v in by_rule.items():
            draws[r][i] = (w @ v) / t

    def ci(x):
        return [float(np.percentile(x, 2.5)), float(np.percentile(x, 97.5))]

    out = {f"{r}_M1_ci": ci(d) for r, d in draws.items()}
    for r in ("R2", "R3", "R4"):
        out[f"{r}_minus_R1_M1"] = float((by_rule[r].sum() - by_rule["R1"].sum()) / total.sum())
        out[f"{r}_minus_R1_M1_ci"] = ci(draws[r] - draws["R1"])
    out["clusters"] = int(n)
    return out
