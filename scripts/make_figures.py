"""Figures for the README and memo, from reports/tables.

PYTHONPATH=src python scripts/make_figures.py
"""

from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from retail.db import ROOT  # noqa: E402

TABLES = ROOT / "reports" / "tables"
FIGS = ROOT / "reports" / "figures"
BLUE, ORANGE, GREY, INK, MUTED, GRID = "#2a78d6", "#eb6834", "#9a9890", "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
    }
)


def save(fig, name: str) -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGS / name, dpi=160, bbox_inches="tight")
    plt.close(fig)


def fig_kpis() -> None:
    k = pd.read_csv(TABLES / "kpis.csv")
    m = k[k["period_type"] == "month"].copy()
    m["date"] = pd.to_datetime(m["period"])
    full = m[m["date"] < "2011-12-01"]
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.4))
    for ax, col, title, scale, fmt in (
        (axes[0], "net_revenue", "Net revenue per month ($k)", 1e3, "{:.0f}"),
        (axes[1], "active_customers", "Active customers per month", 1, "{:.0f}"),
    ):
        ax.plot(full["date"], full[col] / scale, color=BLUE, lw=2, marker="o", ms=3)
        ax.set_title(title)
        ax.axvline(pd.Timestamp("2010-12-01"), color=GREY, lw=1, ls="--")
        ax.text(pd.Timestamp("2010-12-10"), ax.get_ylim()[1] * 0.97, "year 2 →", color=MUTED, fontsize=8, va="top")
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _, f=fmt: f.format(v)))
        ax.tick_params(axis="x", labelrotation=0)
        ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%b\n%Y"))
        ax.xaxis.set_major_locator(matplotlib.dates.MonthLocator(bymonth=[3, 6, 9, 12]))
    fig.text(0.0, -0.09, "December 2011 (9 days) omitted. Each November peak is the pre-Christmas wholesale season.",
             fontsize=8, color=MUTED)  # fmt: skip
    save(fig, "fig1_monthly_kpis.png")


def fig_pareto() -> None:
    y1 = pd.read_csv(TABLES / "year1_products.csv").sort_values("net_revenue", ascending=False)
    share_products = np.arange(1, len(y1) + 1) / len(y1)
    cum = y1["net_revenue"].clip(lower=0).cumsum() / y1["net_revenue"].clip(lower=0).sum()
    counts = y1["abc"].value_counts()
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    edges = np.cumsum([0, counts["A"], counts["B"], counts["C"]]) / len(y1)
    for (lo, hi), lab, shade in zip(zip(edges[:-1], edges[1:], strict=True), "ABC", ("#eef3fa", "#f6f6f4", "#fbeee8"),
                                    strict=True):  # fmt: skip
        ax.axvspan(lo, hi, color=shade, lw=0)
        ax.text((lo + hi) / 2, 0.06, f"Class {lab}\n{counts[lab]:,} products", ha="center", fontsize=8.5, color=INK)
    ax.plot(share_products, cum, color=BLUE, lw=2)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.02)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1))
    ax.set_xlabel("Share of year-1 products, best-selling first")
    ax.set_title("Year 1: half the range earns 5% of revenue")
    ax.set_ylabel("Cumulative share of net revenue")
    save(fig, "fig2_pareto_year1.png")


def fig_rules() -> None:
    d = json.loads((TABLES / "decision1_range.json").read_text())
    names = {
        "R1": "R1  Class C, new launches protected (primary)",
        "R2": "R2  Class C, no protection",
        "R3": "R3  Fewest orders, same size as R1",
        "R4": "R4  R1 + key-account protection",
    }
    fig, ax = plt.subplots(figsize=(8, 3.2))
    for i, r in enumerate(["R1", "R2", "R3", "R4"]):
        m = d["measures"][r]
        lo, hi = d["bootstrap"][f"{r}_M1_ci"]
        y = 3 - i
        col = BLUE if r in ("R1", "R4") else GREY
        ax.plot([100 * lo, 100 * hi], [y, y], color=col, lw=2, solid_capstyle="round")
        ax.plot(100 * m["M1_revenue_at_risk"], y, "o", color=col, ms=8, mec="white", mew=2)
        ax.text(100 * hi + 0.12, y, f"{100 * m['M1_revenue_at_risk']:.1f}%  ·  {m['products_cut']:,} products cut",
                va="center", fontsize=8.5, color=INK)  # fmt: skip
    ax.axvline(3, color=ORANGE, lw=1.5, ls="--")
    ax.text(3.03, 3.45, "3% guardrail", color=INK, fontsize=8.5)
    ax.set_yticks([3, 2, 1, 0], [names[r] for r in ["R1", "R2", "R3", "R4"]])
    ax.set_xlim(0, 7)
    ax.set_ylim(-0.5, 3.7)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Year-2 net revenue at risk (share of total; 95% interval)")
    ax.set_title("Cut lists chosen on year 1, measured on year 2")
    rb = d["random_baseline_M1"]["median"]
    fig.text(0.0, -0.06, f"A random cut the size of R1 would put {100 * rb:.0f}% of year-2 revenue at risk.",
             fontsize=8, color=MUTED)  # fmt: skip
    save(fig, "fig3_cut_rules.png")


def fig_cancellations() -> None:
    w = pd.read_csv(TABLES / "cancellation_rates.csv")
    d = json.loads((TABLES / "decision2_cancellations.json").read_text())
    watch = w["stock_code"].isin(d["watch_list"])
    fig, ax = plt.subplots(figsize=(5.6, 4.2))
    ax.scatter(100 * w.loc[~watch, "rate_Y1"], 100 * w.loc[~watch, "rate_Y2"], s=10, color=GREY, alpha=0.5,
               lw=0, label=f"Other eligible products ({(~watch).sum():,})")  # fmt: skip
    ax.scatter(100 * w.loc[watch, "rate_Y1"], 100 * w.loc[watch, "rate_Y2"], s=24, color=ORANGE, ec="white",
               lw=0.8, label="Year-1 watch list (50)")  # fmt: skip
    lim = max(100 * w[["rate_Y1", "rate_Y2"]].max().max(), 10) * 1.05
    ax.plot([0, lim], [0, lim], color=MUTED, lw=1, ls="--")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("Year-1 cancellation rate (% of sale lines)")
    ax.set_ylabel("Year-2 cancellation rate (%)")
    ax.set_title(f"Cancellation rates persist (Spearman {d['spearman']:.2f})")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    ax.text(lim * 0.97, lim * 0.78, "same rate\nboth years", ha="right", fontsize=8, color=MUTED)
    save(fig, "fig4_cancellation_persistence.png")


def fig_rolling() -> None:
    r = json.loads((TABLES / "rolling_origins.json").read_text())["origins"]
    d1 = json.loads((TABLES / "decision1_range.json").read_text())
    rows = [("Dec 2009-May 2010\n-> Jun-Nov 2010", r["2010-06-01"]["measures"], r["2010-06-01"]["M1_ci"])]
    rows.append(("Dec 2009-Nov 2010\n-> Dec 2010-May 2011", r["2010-12-01"]["measures"], r["2010-12-01"]["M1_ci"]))
    rows.append(("Jun 2010-May 2011\n-> Jun-Nov 2011", r["2011-06-01"]["measures"], r["2011-06-01"]["M1_ci"]))
    rows.append(("Dec 2009-Nov 2010\n-> Dec 2010-Nov 2011 (main)", d1["measures"],
                 {k: d1["bootstrap"][f"{k}_M1_ci"] for k in ("R1", "R2", "R3", "R4")}))  # fmt: skip
    fig, ax = plt.subplots(figsize=(8.4, 3.8))
    cols = {"R1": BLUE, "R2": GREY, "R3": "#c9a227", "R4": ORANGE}
    names = {
        "R1": "R1 class C",
        "R2": "R2 no launch protection",
        "R3": "R3 fewest orders",
        "R4": "R4 key-account protected",
    }
    for i, (_label, m, ci) in enumerate(rows):
        for j, k in enumerate(("R1", "R2", "R3", "R4")):
            y = i + (j - 1.5) * 0.17
            lo, hi = ci[k]
            ax.plot([100 * lo, 100 * hi], [y, y], color=cols[k], lw=2, solid_capstyle="round")
            ax.plot(100 * m[k]["M1_revenue_at_risk"], y, "o", color=cols[k], ms=6, mec="white", mew=1.2,
                    label=names[k] if i == 0 else None)  # fmt: skip
    ax.axvline(3, color=INK, lw=1.2, ls="--")
    ax.text(3.06, -0.42, "3% guardrail", fontsize=8.5, color=INK, va="center")
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=8.5)
    ax.invert_yaxis()
    ax.set_xlabel("Revenue at risk in the test window (% of that window's net revenue; 95% interval)")
    ax.set_title("R4 puts the least revenue at risk at every cut-off date")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=4)
    save(fig, "fig5_rolling_origins.png")


def main() -> None:
    fig_kpis()
    fig_pareto()
    fig_rules()
    fig_rolling()
    fig_cancellations()


if __name__ == "__main__":
    main()
