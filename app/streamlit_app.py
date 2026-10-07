"""Retail operations dashboard: KPIs, the range review and the cancellation watch list.

    streamlit run app/streamlit_app.py

Reads the tables written by scripts/run_analysis.py (reports/tables); no raw data is needed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from retail.scenario import Assumptions, economics  # noqa: E402

TABLES = Path(__file__).resolve().parents[1] / "reports" / "tables"
BLUE, ORANGE, GREY = "#2a78d6", "#eb6834", "#9a9890"

st.set_page_config(page_title="Retail Operations Dashboard", layout="wide")


@st.cache_data
def load():
    kpis = pd.read_csv(TABLES / "kpis.csv")
    cut = pd.read_csv(TABLES / "cut_list_R1.csv")
    products = pd.read_csv(TABLES / "year1_products.csv")
    canc = pd.read_csv(TABLES / "cancellation_rates.csv")
    d1 = json.loads((TABLES / "decision1_range.json").read_text())
    d2 = json.loads((TABLES / "decision2_cancellations.json").read_text())
    notes = json.loads((TABLES / "kpi_notes.json").read_text())
    return kpis, cut, products, canc, d1, d2, notes


kpis, cut, products, canc, d1, d2, notes = load()

st.title("Retail operations dashboard")
st.caption(
    "UK online giftware retailer, every invoice line December 2009 to December 2011 (UCI Online Retail II). "
    "Product lines only; revenue in US dollars before cost, converted from British pounds at $1.5774 per £1 "
    "(the Federal Reserve's average rate over the period). Year 1 = Dec 2009 to Nov 2010, "
    "year 2 = Dec 2010 to Nov 2011."
)

tab_kpi, tab_range, tab_whatif, tab_canc, tab_about = st.tabs(
    ["KPIs", "Range review", "What if", "Cancellations", "Method"]
)

KPI_LABELS = {
    "net_revenue": ("Net revenue", "${:,.0f}"),
    "orders": ("Orders", "{:,.0f}"),
    "average_order_value": ("Average order value", "${:,.0f}"),
    "active_customers": ("Active customers", "{:,.0f}"),
    "cancellation_rate": ("Cancellation rate", "{:.1%}"),
    "returning_customer_share": ("Returning-customer share of sales", "{:.1%}"),
    "sales_without_customer_id": ("Sales without customer ID", "{:.1%}"),
    "international_share": ("International share of sales", "{:.1%}"),
    "products_sold": ("Products sold", "{:,.0f}"),
}

with tab_kpi:
    w = kpis[kpis["period_type"] == "window"].set_index("period")
    y1, y2 = w.loc["Y1"], w.loc["Y2"]
    st.subheader("Year 2 against year 1")
    cols = st.columns(4)
    for i, key in enumerate(["net_revenue", "orders", "average_order_value", "active_customers",
                             "cancellation_rate", "returning_customer_share", "international_share",
                             "products_sold"]):  # fmt: skip
        label, fmt = KPI_LABELS[key]
        change = y2[key] - y1[key]
        if key == "returning_customer_share":
            delta = None  # year 1 is zero by construction (see the note below)
        elif "{:.1%}" in fmt:
            delta = f"{100 * change:+.1f} pts"
        else:
            delta = f"{change / y1[key]:+.1%}"
        # A rising cancellation rate is bad; Streamlit's "inverse" colors it red.
        cols[i % 4].metric(label, fmt.format(y2[key]), delta,
                           delta_color="inverse" if key == "cancellation_rate" else "normal")  # fmt: skip
    adj = notes["cancellation_rate_without_giant_order"]
    st.caption(
        f"Year 2's cancellation rate includes one cancelled ${notes['giant_order_value_usd'] / 1000:,.0f}k order "
        f"(74,215 units, January 2011). Without it the "
        f"rate is {adj['Y2']:.1%}, below year 1's {adj['Y1']:.1%}: the rise is that single event, not a trend."
    )
    st.caption("Returning-customer share has no year-1 comparison: the data starts in December 2009, so every "
               "year-1 customer counts as new.")  # fmt: skip

    st.subheader("Monthly trend")
    key = st.selectbox("KPI", list(KPI_LABELS), format_func=lambda k: KPI_LABELS[k][0])
    m = kpis[kpis["period_type"] == "month"].copy()
    m["month"] = pd.to_datetime(m["period"])
    m["partial"] = m["period"] == "2011-12"
    if key == "returning_customer_share":
        m = m[m["month"] >= "2010-01-01"]
    fmt_axis = ".0%" if "%" in KPI_LABELS[key][1] else ("$,.0f" if "$" in KPI_LABELS[key][1] else ",.0f")
    base = alt.Chart(m).encode(
        x=alt.X("month:T", title=None),
        y=alt.Y(f"{key}:Q", title=KPI_LABELS[key][0], axis=alt.Axis(format=fmt_axis)),
        tooltip=[
            alt.Tooltip("period:N", title="Month"),
            alt.Tooltip(f"{key}:Q", title=KPI_LABELS[key][0], format=fmt_axis),
        ],  # fmt: skip
    )
    line = base.transform_filter("!datum.partial").mark_line(color=BLUE, strokeWidth=2, point=alt.OverlayMarkDef(
        color=BLUE, size=30))  # fmt: skip
    partial = base.transform_filter("datum.partial").mark_point(color=GREY, size=40, filled=True)
    st.altair_chart((line + partial).properties(height=320), width="stretch")
    st.caption("Grey point: December 2011, nine days only.")
    with st.expander("KPI table"):
        st.dataframe(kpis, width="stretch", hide_index=True)

with tab_range:
    st.subheader("Which products to discontinue")
    meas = d1["measures"]
    rule_names = {
        "R1": "Class C tail, new launches protected (primary rule)",
        "R2": "Class C tail, no protection",
        "R3": "Fewest orders, same size as R1",
        "R4": "Class C tail minus products bought by 3+ key accounts (recommended)",
    }
    table = pd.DataFrame([
        {
            "Rule": rule_names[r],
            "Products cut": m["products_cut"],
            "Year-2 revenue at risk": m["M1_revenue_at_risk"],
            "95% interval": "{:.1%} to {:.1%}".format(*d1["bootstrap"][f"{r}_M1_ci"]),
            "Picks removed": m["M4_share_of_sale_lines"],
            "Customers affected": m["M5_share_of_customers_touched"],
            "Became year-2 class A/B": m["M3_false_cuts"],
        }
        for r, m in meas.items()
    ])  # fmt: skip
    st.dataframe(
        table.style.format(
            {"Year-2 revenue at risk": "{:.1%}", "Picks removed": "{:.1%}", "Customers affected": "{:.0%}"}
        ),  # fmt: skip
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Each list was chosen on year-1 data and measured on year 2. The guardrail agreed beforehand was at most 3% "
        f"of year-2 revenue at risk. A random cut the size of R1 would risk "
        f"{d1['random_baseline_M1']['median']:.0%}. Revenue at risk assumes no customer switches to a substitute."
    )

    st.subheader("Cut list")
    which = st.radio("List", ["Recommended (R4)", "Primary rule (R1)"], horizontal=True)
    q = st.text_input("Search product description or code")
    view = cut[cut["in_R4"]] if which.startswith("Recommended") else cut
    if q:
        mask = view["description"].fillna("").str.contains(q, case=False) | view["stock_code"].str.contains(
            q, case=False)  # fmt: skip
        view = view[mask]
    st.write(f"{len(view):,} products · year-1 net revenue ${view['year1_net_revenue'].sum():,.0f} · "
             f"year-2 net revenue ${view['year2_net_revenue'].sum():,.0f}")  # fmt: skip
    shown = view.assign(year1_first_sale=pd.to_datetime(view["year1_first_sale"]).dt.date).rename(columns={
        "stock_code": "Code", "description": "Description", "year1_net_revenue": "Y1 net revenue ($)",
        "year1_orders": "Y1 orders", "year1_customers": "Y1 customers", "year1_first_sale": "Y1 first sale",
        "key_account_buyers": "Key-account buyers", "year2_net_revenue": "Y2 net revenue ($)",
        "year2_sale_lines": "Y2 sale lines", "in_R4": "In R4"})  # fmt: skip
    st.dataframe(shown, width="stretch", hide_index=True)
    st.download_button("Download this list (CSV)", view.to_csv(index=False), file_name="cut_list.csv")

    st.subheader("Does the ranking hold at other dates?")
    ro = json.loads((TABLES / "rolling_origins.json").read_text())["origins"]
    rows = []
    for _cut, v in ro.items():
        m = v["measures"]
        rows.append(
            {
                "Trained on": f"{v['train'][0]} to {v['train'][1]}",
                "Tested on": f"{v['test'][0]} to {v['test'][1]}",
                "R1 at risk": m["R1"]["M1_revenue_at_risk"],
                "R4 at risk": m["R4"]["M1_revenue_at_risk"],
                "R2 at risk": m["R2"]["M1_revenue_at_risk"],
            }
        )
    st.dataframe(
        pd.DataFrame(rows).style.format({c: "{:.1%}" for c in ["R1 at risk", "R4 at risk", "R2 at risk"]}),
        width="stretch",
        hide_index=True,
    )
    st.caption("Same four rules, three more cut-off dates, each using only earlier data. R4 is lowest every time.")

    st.subheader("Year-1 ABC classes")
    abc = products.groupby("abc").agg(products=("stock_code", "size"), revenue=("net_revenue", "sum")).reset_index()
    abc["share_of_revenue"] = abc["revenue"] / abc["revenue"].sum()
    abc["share_of_products"] = abc["products"] / abc["products"].sum()
    st.dataframe(
        abc.style.format({"revenue": "${:,.0f}", "share_of_revenue": "{:.1%}", "share_of_products": "{:.1%}"}),
        hide_index=True,
    )

with tab_whatif:
    st.subheader("Does the cut pay? It depends on costs the data doesn't have")
    st.write(
        "The dataset has no product cost or stock data, so set your own. Revenue at risk is an upper bound "
        "(it assumes no customer switches to a substitute product)."
    )
    c1, c2, c3 = st.columns(3)
    margin = c1.slider("Gross margin", 0.10, 0.70, 0.40, 0.05)
    pick = c2.slider("Cost per order line picked ($)", 0.0, 3.0, 0.50, 0.10)
    listing = c3.slider("Yearly cost of carrying one listing ($)", 0, 300, 0, 10)
    y2_lines = float(kpis[(kpis["period_type"] == "window") & (kpis["period"] == "Y2")]["sale_lines"].iloc[0])
    rows = []
    for r, label in (
        ("R1", "Class C tail, new launches protected"),
        ("R4", "Same, minus key-account products (recommended)"),
    ):
        e = economics(d1["measures"][r], y2_lines, Assumptions(margin, pick, listing))
        rows.append(
            {
                "Rule": label,
                "Products cut": e["products_cut"],
                "Margin lost ($)": e["gross_margin_lost"],
                "Pick cost saved ($)": e["pick_cost_saved"],
                "Listing cost saved ($)": e["listing_cost_saved"],
                "Net benefit ($)": e["net_benefit"],
                "Break-even $ per listing per year": e["break_even_cost_per_listing"],
            }
        )
    st.dataframe(
        pd.DataFrame(rows).style.format(
            {
                c: "{:,.0f}"
                for c in ["Margin lost ($)", "Pick cost saved ($)", "Listing cost saved ($)", "Net benefit ($)"]
            }
            | {"Break-even $ per listing per year": "{:,.0f}"}
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        "Break-even is the yearly cost per listing above which the cut pays for itself. If carrying a product costs "
        "more than that (catalogue upkeep, a storage slot, stock tied up), cutting it adds profit."
    )

with tab_canc:
    st.subheader("Do cancellation problems persist?")
    c1, c2, c3 = st.columns(3)
    c1.metric(
        "Year-1 to year-2 rank correlation",
        f"{d2['spearman']:.2f}",
        help="Spearman correlation of product cancellation rates, products with 20+ sale lines both years",
    )
    c2.metric("Watch list, year-2 cancellation rate", f"{d2['watch_rate_Y2']:.1%}")  # fmt: skip
    c3.metric("Other products, year-2 rate", f"{d2['others_rate_Y2']:.1%}")
    st.caption(
        f"The 50 products with the highest year-1 cancellation rate cancelled at {d2['ratio_Y2']:.1f}× the rate of "
        f"other products in year 2 (95% interval {d2['ratio_Y2_ci'][0]:.1f}–{d2['ratio_Y2_ci'][1]:.1f}×), down from "
        f"{d2['watch_rate_Y1']:.0%} in year 1: part of the gap persists, part regresses."
    )
    pts = canc.assign(group=canc["watch_list"].map({True: "Year-1 watch list", False: "Other products"}))
    chart = (
        alt.Chart(pts)
        .mark_circle(opacity=0.7)
        .encode(
            x=alt.X("rate_Y1:Q", title="Year-1 cancellation rate", axis=alt.Axis(format=".0%")),
            y=alt.Y("rate_Y2:Q", title="Year-2 cancellation rate", axis=alt.Axis(format=".0%")),
            color=alt.Color(
                "group:N",
                scale=alt.Scale(domain=["Other products", "Year-1 watch list"], range=[GREY, ORANGE]),
                legend=alt.Legend(title=None),
            ),  # fmt: skip
            size=alt.condition("datum.watch_list", alt.value(60), alt.value(20)),
            tooltip=[
                "stock_code",
                "description",
                alt.Tooltip("rate_Y1:Q", format=".1%"),
                alt.Tooltip("rate_Y2:Q", format=".1%"),
                "sale_lines_Y2",
            ],  # fmt: skip
        )
    )
    st.altair_chart(chart.properties(height=380), width="stretch")
    st.subheader("Watch list for listing review")
    wl = canc[canc["watch_list"]].sort_values("rate_Y1", ascending=False)[
        ["stock_code", "description", "sale_lines_Y1", "rate_Y1", "sale_lines_Y2", "rate_Y2"]
    ].rename(columns={"stock_code": "Code", "description": "Description", "sale_lines_Y1": "Y1 sale lines",
                      "rate_Y1": "Y1 cancellation rate", "sale_lines_Y2": "Y2 sale lines",
                      "rate_Y2": "Y2 cancellation rate"})  # fmt: skip
    st.dataframe(wl.style.format({"Y1 cancellation rate": "{:.1%}", "Y2 cancellation rate": "{:.1%}",
                                  "Y1 sale lines": "{:,.0f}", "Y2 sale lines": "{:,.0f}"}),
                 width="stretch", hide_index=True)  # fmt: skip

with tab_about:
    st.markdown(
        """
**How this was built.** Raw invoice lines are staged in SQL (DuckDB). Staging removes the 22,523 rows the two
source sheets duplicate, keeps the first copy of exact duplicate lines, and classifies every line: sale,
cancellation, stock adjustment, postage or fee. The KPIs are defined in SQL, and both decisions follow an
analysis plan committed before any year-2 product result was computed.

**Limits.** There is no cost or margin data, so the range review uses revenue only. Revenue at risk is an upper
bound, because it assumes no substitution. The test covers one year-to-year transition.

Code, analysis plan and memo:
[github.com/Andresperez397/retail-operations-case-study](https://github.com/Andresperez397/retail-operations-case-study)
"""
    )
