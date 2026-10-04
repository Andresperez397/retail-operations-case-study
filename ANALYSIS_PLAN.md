# Analysis plan

Written 2026-10-04, after the data audit and before any product-level result for year 2 was computed. It is frozen by its git commit. Every later change is logged in [DEVIATIONS.md](DEVIATIONS.md), including exploratory checks, which are labelled as such.

## The business setting

**The retailer:** a UK online giftware retailer that sold about 4,000 different products in year 1 (December 2009 to November 2010). Many of them sell rarely. Each listed product costs money that the data does not show: catalogue space, a warehouse pick location, stock that may not sell.

**The stakeholder:** the head of merchandising, who is planning the next range.

**Decision 1 (primary): which products should be discontinued, and how much next-year revenue would the cut put at risk?**

**Decision 2 (secondary): should a short list of products with high cancellation rates be sent for a listing review?** That is only worth doing if cancellation problems persist from one year to the next.

The recommendation must use only what the retailer knew at the end of year 1. It is then tested on year 2 (December 2010 to November 2011), which plays the role of the following year.

## Definitions

**Lines:** product lines from the staged `product_lines` view: kept sales and cancellations of catalogue products. See DATA_AUDIT.md.

**Revenue measures:**
- **Net revenue:** sales value minus cancellation value (quantity × unit price). This is before cost; the data has no margins.
- **Order:** a distinct sales invoice.

**Product groups:**
- **Year-1 range:** every product with at least one sale line in year 1.
- **New launch:** a product whose first year-1 sale is on or after 2010-09-01, the last quarter of year 1. That is too little history to judge it fairly, especially for autumn and Christmas lines.

**Customer groups:**
- **Customer:** a customer ID. Lines without an ID count toward revenue but not toward customer measures.
- **Top-decile customer:** the top 10% of year-1 customers by year-1 net revenue.

**ABC classes** (standard inventory practice): products are sorted by net revenue, high to low. Class A is the products making up the first 80% of cumulative net revenue, class B the next 15%, and class C the final 5%, including products with zero or negative net revenue.

## Decision 1: cut rules

All rules are computed from year-1 data only.

| Rule | Role | Cut list |
|---|---|---|
| **R1** | **primary** | Year-1 class C products, excluding new launches |
| R2 | secondary | Year-1 class C products, new launches included: tests whether the protection matters |
| R3 | secondary | **Same number of products as R1**, chosen by fewest distinct year-1 orders, with new launches excluded: tests whether a breadth rule beats a revenue rule at equal size |
| R4 | secondary | R1, minus products bought by at least 3 distinct top-decile customers in year 1: key-account protection |

## Decision 1: year-2 measures

**M1 (primary): revenue at risk.** The year-2 net revenue of the cut products, as a share of total year-2 net product revenue. This is an upper bound on the loss, because it assumes no customer switches to a substitute product.

**M2:** the share of cut products that still sold in year 2. The rest had already dropped out of the range, so cutting them costs nothing.

**M3: false cuts.** The number of cut products that reach year-2 class A or B.

**M4: workload removed.** The share of year-2 sale lines that belong to cut products. Each sale line is a warehouse pick, so this is a proxy.

**M5: customers touched.** The share of year-2 customers who bought at least one cut product.

**Baselines:**
- **Random cut:** a random cut of the same size from the eligible range, matching R1 (year-1 range minus new launches). 1,000 draws, seed 2026; the median and the 2.5–97.5th percentiles of M1 are reported.

**Uncertainty:** 95% intervals for M1 and for the differences R2 − R1, R3 − R1 and R4 − R1. They come from a cluster bootstrap over year-2 customers: 1,000 replicates, seed 2026. Lines without a customer ID are clustered by invoice.

**Pre-specified hypotheses and decision criterion:**
- **H1 (decision criterion):** R1 puts at most 3% of year-2 net revenue at risk (M1 ≤ 3%). The 3% is the guardrail a merchandising team would set before agreeing to a cut. If H1 holds, the memo recommends R1. If it fails, the memo reports that the C-tail is not safe to cut on revenue alone.
- **H2:** new-launch protection matters. R2 has more false cuts (M3) than R1 and puts more revenue at risk.
- **H3:** at equal size, the breadth rule R3 puts less revenue at risk than the revenue rule R1. No direction is assumed; this is two-sided.
- **H4:** key-account protection lowers revenue at risk (R4 < R1).

## Decision 2: cancellation persistence

- **Eligible products:** those with at least 20 sale lines in **each** year.
- **Cancellation rate:** a product's cancellation lines divided by its sale lines in that year. The rate counts lines, not value, so the two giant order-and-cancel pairs cannot dominate it.
- **H5:** cancellation rates persist from one year to the next: Spearman correlation between year-1 and year-2 rates greater than 0, with a 95% bootstrap interval over products (1,000 replicates, seed 2026).
- **Watch list:** the 50 eligible products with the highest year-1 cancellation rate.
- **H6:** the watch list's pooled year-2 cancellation rate exceeds that of all other eligible products. A 95% interval for the ratio comes from a bootstrap over products.
- **Decision rule:** if both H5 and H6 hold, the memo recommends a listing review for the products with the highest cancellation rates, refreshed each year. If not, cancellations are better treated as one-off events.

## KPI layer and dashboard

The KPI definitions are written in [KPI_DEFINITIONS.md](KPI_DEFINITIONS.md) and computed in SQL ([sql/02_kpis.sql](sql/02_kpis.sql)). They are descriptive and carry no hypotheses. The dashboard shows:
- the monthly KPIs
- the year-1 ABC classes
- the R1 cut list.

## Sensitivity checks (pre-specified)

- **S1:** keep the 11,812 exact duplicate lines and rerun M1 for R1.
- **S2:** move the new-launch cutoff to 2010-08-01 and to 2010-10-01.
- **S3:** ABC split at 70/20/10, so class C is the final 10%; rerun M1 for R1.

## What would change the conclusions

- **M1 is an upper bound:** if customers switch to similar products, the real loss is smaller.
- **No cost data:** the memo states that a cut list based on revenue alone ignores margin, stock and storage cost. A real decision would add them.
- **One out-of-time year:** the result describes one transition, 2010 to 2011.
