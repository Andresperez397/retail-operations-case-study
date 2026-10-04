"""Decision 2: do product cancellation rates persist from year 1 to year 2? (see ANALYSIS_PLAN.md)"""

from __future__ import annotations

import numpy as np
import pandas as pd


def eligible_rates(product_year: pd.DataFrame, min_lines: int = 20) -> pd.DataFrame:
    """Products with at least `min_lines` sale lines in both years, with line-based cancellation rates."""
    wide = product_year.pivot(index="stock_code", columns="analysis_year", values=["sale_lines", "cancel_lines"])
    wide.columns = [f"{a}_{b}" for a, b in wide.columns]
    wide = wide.fillna(0)
    ok = (wide["sale_lines_Y1"] >= min_lines) & (wide["sale_lines_Y2"] >= min_lines)
    w = wide[ok].copy()
    w["rate_Y1"] = w["cancel_lines_Y1"] / w["sale_lines_Y1"]
    w["rate_Y2"] = w["cancel_lines_Y2"] / w["sale_lines_Y2"]
    return w


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = pd.Series(x).rank().to_numpy()
    ry = pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def persistence(w: pd.DataFrame, watch_size: int = 50, reps: int = 1000, seed: int = 2026) -> dict:
    rng = np.random.default_rng(seed)
    x, y = w["rate_Y1"].to_numpy(), w["rate_Y2"].to_numpy()
    rho = spearman(x, y)
    boot = []
    for _ in range(reps):
        i = rng.integers(0, len(w), len(w))
        boot.append(spearman(x[i], y[i]))

    ranked = w.reset_index().sort_values(["rate_Y1", "stock_code"], ascending=[False, True])
    watch = ranked.head(watch_size)
    others = ranked.iloc[watch_size:]

    def pooled(d: pd.DataFrame) -> float:
        return d["cancel_lines_Y2"].sum() / d["sale_lines_Y2"].sum()

    ratio = pooled(watch) / pooled(others)
    ratios = []
    for _ in range(reps):
        a = watch.iloc[rng.integers(0, len(watch), len(watch))]
        b = others.iloc[rng.integers(0, len(others), len(others))]
        ratios.append(pooled(a) / pooled(b))
    return {
        "eligible_products": int(len(w)),
        "spearman": rho,
        "spearman_ci": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))],
        "watch_list_size": int(len(watch)),
        "watch_rate_Y1": float(watch["cancel_lines_Y1"].sum() / watch["sale_lines_Y1"].sum()),
        "watch_rate_Y2": float(pooled(watch)),
        "others_rate_Y1": float(others["cancel_lines_Y1"].sum() / others["sale_lines_Y1"].sum()),
        "others_rate_Y2": float(pooled(others)),
        "ratio_Y2": float(ratio),
        "ratio_Y2_ci": [float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5))],
        "watch_list": watch["stock_code"].tolist(),
    }
