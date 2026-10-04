# Data audit

Run on 2026-10-04 with `scripts/data_audit.py`, before the analysis plan was written. It reports data-structure facts and whole-window totals only; no product-level results for year 2 were computed. Full output: [reports/tables/data_audit.json](reports/tables/data_audit.json).

**Currency:** the source records prices in British pounds. All amounts in this project are shown in US dollars, converted at one fixed rate: $1.5774 per £1, the Federal Reserve's average daily rate over the data period (FRED series DEXUSUK). Because the rate is fixed, no count, share or decision depends on it.

## Source

**Dataset:** UCI Online Retail II (Chen, 2019; [doi:10.24432/C5CG6D](https://doi.org/10.24432/C5CG6D); CC BY 4.0).
**Business:** a UK-based online retailer of giftware. Many customers are wholesalers.
**Contents:** every invoice line from 1 December 2009 to 9 December 2011, delivered as one Excel workbook with two sheets:

| Sheet | Rows | First line | Last line |
|---|---|---|---|
| Year 2009-2010 | 525,461 | 2009-12-01 07:45 | 2010-12-09 20:01 |
| Year 2010-2011 | 541,910 | 2010-12-01 08:26 | 2011-12-09 12:50 |

**Columns:** invoice, stock code, description, quantity, invoice date, unit price, customer ID and country.
**What is not included:** product cost (so there is no margin data), stock levels and delivery times.

## Problems found and how staging handles them

All handling is in [sql/01_staging.sql](sql/01_staging.sql). Every raw row is kept in the staged table with a status, so each exclusion is counted.

| # | Problem | Rows | Handling |
|---|---|---|---|
| 1 | **The sheets overlap.** The 2010-2011 sheet repeats 1-9 December 2010, which the 2009-2010 sheet already covers. All 22,523 repeated rows are identical to their counterparts. | 22,523 | Dropped from the 2010-2011 sheet. Loading both sheets as delivered would double-count that week. |
| 2 | **Exact duplicate lines:** same invoice, product, description, quantity, minute, price and customer. | 11,812 extra copies | First copy kept. They may be genuine double entries; the plan reports a sensitivity check with them kept. |
| 3 | **Cancellations.** Invoices starting with `C` reverse earlier sales (negative quantity). | 17,915 product lines (−$1.13M) | Kept as negative revenue on the product. Net revenue = sales − cancellations. |
| 4 | **Non-product codes:** postage (`POST`, `DOT`, `C2`), manual entries (`M`), discounts, samples, bank charges, Amazon fees, bad-debt adjustments (`B`, invoices starting with `A`), test products and gift vouchers. | 5,800 | Excluded from product analysis. They are not part of the catalogue. |
| 5 | **Stock adjustments:** negative quantities on normal invoices at zero price, described as "damaged", "check", "missing", "?" or left blank. | 3,392 | Excluded from revenue. They are warehouse write-offs, not sales. |
| 6 | **Zero-price lines** with positive quantity. | 2,572 | Excluded from revenue. |
| 7 | **Lower-case stock codes** (e.g. `85123a` alongside `85123A`). | 3,471 | Upper-cased, so each product has one code. |
| 8 | **Several descriptions per code:** 600 product codes have more than one description (spelling changes and edits). | — | The stock code identifies the product. |
| 9 | **Missing customer ID:** 22.6% of sale lines and 13.1% of sales value. | 226,761 sale lines | Kept in all revenue figures. Excluded only from customer counts and customer-level metrics. |
| 10 | **Giant order-and-cancel pairs.** 80,995 units of one paper-craft product (December 2011), and 74,215 units of a storage jar (January 2011), each cancelled within 20 minutes. | 4 lines | Kept. Each cancellation nets its order to zero. Line-count measures are not distorted by them. |

No value failed to parse: every quantity, date and price converts cleanly.

## After staging

| Window | Dates | Product lines | Orders | Products sold | Customers (with ID) | Net product revenue |
|---|---|---|---|---|---|---|
| Year 1 | 2009-12-01 to 2010-11-30 | 490,064 | 19,743 | 4,073 | 4,267 | $14.44M |
| Year 2 | 2010-12-01 to 2011-11-30 | 506,108 | 18,957 | 3,797 | 4,321 | $14.72M |
| December 2011 (partial) | 2011-12-01 to 2011-12-09 | 25,100 | 816 | 2,433 | 684 | $0.69M |

**Why these windows:** both analysis years run December to November, so each holds one full Christmas season. The nine days of December 2011 appear in the KPI dashboard but not in the year-on-year analysis.
