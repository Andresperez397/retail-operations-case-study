"""What-if economics for the cut rules, under stated assumptions.

The dataset has no product cost, margin or stock data, so the range review measures revenue at risk. This module turns
that into a profit view for any assumptions the reader chooses:

    gross margin lost   = revenue at risk x gross margin   (an upper bound: no customer switches to a substitute)
    pick cost saved     = year-2 sale lines of the cut products x cost per pick
    listing cost saved  = products cut x annual cost of carrying one listing (catalogue, storage slot, stock tied up)
    net benefit         = pick cost saved + listing cost saved - gross margin lost

and the break-even cost of carrying one listing: the annual cost per listing above which the cut pays for itself.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Assumptions:
    gross_margin: float = 0.40  # share of revenue left after product cost
    cost_per_pick: float = 0.50  # dollars to pick, pack and handle one order line
    cost_per_listing_year: float = 0.0  # dollars per year to carry one product listing


def economics(rule: dict, y2_sale_lines_total: float, a: Assumptions) -> dict:
    """`rule` is one entry of decision1_range.json["measures"]."""
    lost = rule["M1_revenue_at_risk_usd"] * a.gross_margin
    picks = rule["M4_share_of_sale_lines"] * y2_sale_lines_total * a.cost_per_pick
    listing = rule["products_cut"] * a.cost_per_listing_year
    net = picks + listing - lost
    # Annual cost per listing at which net benefit is exactly zero (never negative: a free cut can still win on picks).
    break_even = max((lost - picks) / rule["products_cut"], 0.0) if rule["products_cut"] else float("nan")
    return {
        "products_cut": rule["products_cut"],
        "gross_margin_lost": lost,
        "pick_cost_saved": picks,
        "listing_cost_saved": listing,
        "net_benefit": net,
        "break_even_cost_per_listing": break_even,
    }
