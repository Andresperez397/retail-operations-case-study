# KPI definitions

Each KPI is computed in [sql/02_kpis.sql](sql/02_kpis.sql). The definition is the same at monthly grain and at analysis-window grain (year 1, year 2, December 2011). All figures are in US dollars, converted from the source's British pounds at one fixed rate ($1.5774 per £1, the Federal Reserve's average daily rate over the data period (FRED series DEXUSUK)), and before cost: the data has no product cost, so there is no margin KPI.

All KPIs use catalogue product lines only (sales and their cancellations; see [DATA_AUDIT.md](DATA_AUDIT.md)). Postage, fees, manual entries, stock adjustments and zero-price lines are excluded.

## Sales

| KPI | Definition | Notes |
|---|---|---|
| Gross sales | Σ quantity × unit price over sale lines | |
| Cancelled value | Σ quantity × unit price over cancellation lines, shown as a positive number | Counted in the period of the cancellation, which can differ from the period of the sale. |
| **Net revenue** | Gross sales − cancelled value | The headline revenue figure. |
| Cancellation rate | Cancelled value ÷ gross sales | Value-based, so single giant orders dominate it: one cancelled 80,995-unit order puts December 2011 at 28%, and one 74,215-unit order lifts year 2 from 2.4% to 3.1%. The dashboard shows year 2 with and without that order. |
| Orders | Distinct sales invoices | |
| Average order value | Gross sales ÷ orders | Wholesale customers make this high (about $800). |

## Customers

All customer KPIs count customer IDs. Lines without an ID count toward sales but not here.

| KPI | Definition | Notes |
|---|---|---|
| Active customers | Customers with at least one sale line in the period | |
| New customers | Active customers whose first purchase falls in the period | The data starts in December 2009, so every customer looks new in December 2009 and across all of year 1. Read new-customer trends from early 2010 on. |
| Returning-customer share | Sales from customers whose first purchase came before the period ÷ sales with a customer ID | |
| Sales without customer ID | Sales on lines with no customer ID ÷ gross sales | A data-capture KPI: those sales cannot be tied to anyone. |

## Range and reach

| KPI | Definition |
|---|---|
| International share | Sales to customers outside the United Kingdom ÷ gross sales |
| Products sold | Distinct stock codes with at least one sale line in the period |
| Sale lines | Count of sale lines: one per product per order, a proxy for warehouse picks |

## Product classes (range analysis)

**ABC class.** Products are sorted by net revenue in a window, highest first:
- **class A:** the products making up the first 80% of cumulative net revenue
- **class B:** the next 15%
- **class C:** the remaining 5%, including products with zero or negative net revenue.

**New launch.** A product whose first year-1 sale is on or after 1 September 2010.

The cut rules built on these classes are defined in [ANALYSIS_PLAN.md](ANALYSIS_PLAN.md).
