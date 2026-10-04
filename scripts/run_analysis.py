"""Run the KPI layer and both pre-registered decisions; write tables to reports/tables.

PYTHONPATH=src python scripts/run_analysis.py
"""

from __future__ import annotations

import json
import math

import pandas as pd

from retail import cancellations
from retail import range as rng_
from retail.db import ROOT, SQL, run_sql, staged

TABLES = ROOT / "reports" / "tables"


def product_year(con, source: str = "product_lines") -> pd.DataFrame:
    con.execute((SQL / "03_product_year.sql").read_text().replace("FROM product_lines", f"FROM {source}"))
    return con.execute("SELECT * FROM product_year ORDER BY stock_code, analysis_year").fetchdf()


def key_account_counts(con, source: str = "product_lines") -> pd.Series:
    """Distinct top-decile year-1 customers (by year-1 net revenue) buying each product in year 1."""
    cust = con.execute(
        f"SELECT customer_id, sum(line_value) AS net FROM {source} WHERE analysis_year = 'Y1' "
        "AND customer_id IS NOT NULL GROUP BY 1 HAVING count(*) FILTER (WHERE line_type = 'sale') > 0"
    ).fetchdf()
    top = cust.sort_values(["net", "customer_id"], ascending=[False, True]).head(math.ceil(0.1 * len(cust)))
    pairs = con.execute(
        f"SELECT DISTINCT stock_code, customer_id FROM {source} WHERE analysis_year = 'Y1' AND line_type = 'sale' "
        "AND customer_id IS NOT NULL"
    ).fetchdf()
    return pairs[pairs["customer_id"].isin(top["customer_id"])].groupby("stock_code")["customer_id"].nunique()


def y2_customer_pairs(con, source: str = "product_lines") -> pd.DataFrame:
    return con.execute(
        f"SELECT DISTINCT stock_code, customer_id FROM {source} WHERE analysis_year = 'Y2' AND line_type = 'sale' "
        "AND customer_id IS NOT NULL"
    ).fetchdf()


def decision1(con, py: pd.DataFrame, source: str = "product_lines", cutoff=rng_.NEW_LAUNCH_CUTOFF, a=0.80, b=0.95):
    y1 = rng_.year1_frame(py, key_account_counts(con, source), cutoff, a, b)
    y2 = py[py["analysis_year"] == "Y2"].set_index("stock_code")
    cuts = rng_.cut_lists(y1)
    pairs = y2_customer_pairs(con, source)
    measures = {r: rng_.year2_measures(c, y2, pairs) for r, c in cuts.items()}
    return y1, y2, cuts, measures


def main() -> None:
    con = staged()
    run_sql(con, "02_kpis.sql")
    TABLES.mkdir(parents=True, exist_ok=True)
    kpis = con.execute("SELECT * FROM kpis ORDER BY period_type, period").fetchdf()
    kpis.to_csv(TABLES / "kpis.csv", index=False)
    # Value-based KPIs without the one giant order-and-cancel pair in the analysis years (74,215 units, January
    # 2011; see DEVIATIONS.md), so the dashboard can show how much of a change that single event explains.
    giant = ("541431", "C541433")
    notes = con.execute(
        "SELECT analysis_year, -sum(line_value) FILTER (WHERE line_type = 'cancellation') "
        "/ sum(line_value) FILTER (WHERE line_type = 'sale') FROM product_lines "
        "WHERE analysis_year IN ('Y1', 'Y2') AND invoice NOT IN (?, ?) GROUP BY 1 ORDER BY 1",
        list(giant),
    ).fetchall()
    kpi_notes = {"excluded_invoices": list(giant), "cancellation_rate_without_giant_order": dict(notes)}
    (TABLES / "kpi_notes.json").write_text(json.dumps(kpi_notes, indent=2))

    py = product_year(con)
    y1, y2, cuts, measures = decision1(con, py)
    eligible = sorted(y1.index[~y1["new_launch"]])
    y2_lines = con.execute(
        "SELECT stock_code, customer_id, invoice, line_value FROM product_lines WHERE analysis_year = 'Y2' "
        "ORDER BY row_id"
    ).fetchdf()
    d1 = {
        "year1_range": int(len(y1)),
        "year1_new_launches": int(y1["new_launch"].sum()),
        "year1_abc_counts": y1["abc"].value_counts().sort_index().to_dict(),
        "year1_abc_revenue_share": (y1.groupby("abc")["net_revenue"].sum() / y1["net_revenue"].sum()).to_dict(),
        "year1_c_class_revenue_gbp": float(y1.loc[y1["abc"] == "C", "net_revenue"].sum()),
        "year2_net_revenue_gbp": float(y2["net_revenue"].sum()),
        "measures": measures,
        "random_baseline_M1": rng_.random_baseline(eligible, len(cuts["R1"]), y2),
        "bootstrap": rng_.cluster_bootstrap(y2_lines, cuts),
    }
    d1["H1_R1_at_most_3pct"] = measures["R1"]["M1_revenue_at_risk"] <= 0.03

    # Pre-specified sensitivity checks on R1.
    con.execute(
        "CREATE OR REPLACE VIEW product_lines_with_duplicates AS SELECT * FROM lines "
        "WHERE row_status IN ('kept', 'dropped: exact duplicate') AND line_type IN ('sale', 'cancellation')"
    )
    s1_py = product_year(con, "product_lines_with_duplicates")
    sens = {"S1_duplicates_kept": decision1(con, s1_py, "product_lines_with_duplicates")[3]["R1"]}
    product_year(con)  # restore the primary table
    for label, cutoff in (("S2_cutoff_2010-08-01", "2010-08-01"), ("S2_cutoff_2010-10-01", "2010-10-01")):
        sens[label] = decision1(con, py, cutoff=pd.Timestamp(cutoff))[3]["R1"]
    sens["S3_abc_70_20_10"] = decision1(con, py, a=0.70, b=0.90)[3]["R1"]
    d1["sensitivity_R1"] = sens
    (TABLES / "decision1_range.json").write_text(json.dumps(d1, indent=2))

    cut = y1.loc[cuts["R1"]].reset_index()
    cut["year2_net_revenue"] = y2["net_revenue"].reindex(cut["stock_code"]).fillna(0).to_numpy()
    cut["year2_sale_lines"] = y2["sale_lines"].reindex(cut["stock_code"]).fillna(0).astype(int).to_numpy()
    cut["in_R4"] = cut["stock_code"].isin(cuts["R4"])
    cols = ["stock_code", "description", "net_revenue", "orders", "customers", "first_sale", "key_account_buyers",
            "year2_net_revenue", "year2_sale_lines", "in_R4"]  # fmt: skip
    cut[cols].rename(columns={"net_revenue": "year1_net_revenue", "orders": "year1_orders",
                              "customers": "year1_customers", "first_sale": "year1_first_sale"}).sort_values(
        "year1_net_revenue").to_csv(TABLES / "cut_list_R1.csv", index=False)  # fmt: skip
    y1.reset_index()[["stock_code", "description", "net_revenue", "orders", "customers", "abc", "new_launch",
                      "key_account_buyers"]].to_csv(TABLES / "year1_products.csv", index=False)  # fmt: skip

    w = cancellations.eligible_rates(py)
    d2 = cancellations.persistence(w)
    d2["H5_persistent"] = d2["spearman_ci"][0] > 0
    d2["H6_watch_list_higher"] = d2["ratio_Y2_ci"][0] > 1
    (TABLES / "decision2_cancellations.json").write_text(json.dumps(d2, indent=2))
    w = w.join(y1["description"]).reset_index()
    w["watch_list"] = w["stock_code"].isin(d2["watch_list"])
    w.to_csv(TABLES / "cancellation_rates.csv", index=False)

    print(json.dumps({k: v for k, v in d1.items() if k != "sensitivity_R1"}, indent=2))
    print(json.dumps(sens, indent=2))
    print(json.dumps({k: v for k, v in d2.items() if k != "watch_list"}, indent=2))


if __name__ == "__main__":
    main()
