# Deviations from the analysis plan

The plan was frozen at commit `c7cc004`. This file lists every change made after the freeze, and every check not in the plan.

## Changes to how results are computed

1. **Reproducibility fix (no change to point estimates).** The first run's bootstrap intervals moved in the third decimal from one run to the next. DuckDB returned year-2 lines in an unspecified order, so the bootstrap clusters were numbered differently under the same seed. Parallel summation also changed the last digits of totals.
   - **Fix:** explicit `ORDER BY` on every table the analysis reads, and DuckDB set to one thread.
   - **Effect:** results are now byte-identical across runs. Point estimates did not change; the interval ends moved by at most 0.05 percentage points, the size of ordinary bootstrap noise. All reported numbers come from the fixed version.
2. **KPI definition fix, made before any KPI was reported.** "New customers" and "returning-customer share" were first written against each line's month. At window grain that labels almost everyone new. They now compare a customer's first purchase with the start of the period, at both grains, as KPI_DEFINITIONS.md states.

## Exploratory checks (not in the plan; descriptive only, no effect on any decision rule)

3. **Where R1's revenue at risk comes from:**
   - 81% of R1's year-2 revenue at risk sits in the 1,063 cut products bought by at least three top-decile customers. These are the products R4 protects.
   - The largest single false cuts are low-volume year-1 products that grew in year 2. For example, a rosette went from $652 to $5,687, and two pet bowls went from about $740 and $870 to about $4,100 each.
4. **Natural attrition:** 927 of the 4,073 year-1 products did not sell at all in year 2, and 651 products sold in year 2 that had not sold in year 1. The retailer was already turning over about a fifth of its range each year without a formal rule.
5. **R4 list detail:**
   - 906 products, 22% of the year-1 range
   - $132.1k of year-1 net revenue (0.9%) and $87.2k of year-2 net revenue (0.6%)
   - 368 of the 906 had no year-2 sales.

6. **One order explains year 2's higher cancellation rate.** The year-2 cancellation rate (3.1%, against 2.6% in year 1) includes a single order for 74,215 storage jars ($122k), cancelled 16 minutes after it was placed. Without that pair, year 2 is 2.35%, below year 1's 2.56%. The KPI definition is unchanged; the README and dashboard now report both figures so the change is not read as a trend. The decision analyses are unaffected: the cancellation-persistence test counts lines, not value.
7. **Price outliers.** 92 sale lines are priced more than 20 times their product's median price: 73 lines worth $7.2k in year 1 and 19 worth $62.8k in year 2. The largest is 60 wicker baskets at $1,024.52 each, against a usual $9.39. These look like entry errors but are kept, because the plan did not provide for removing them.
   - **Effect on the decisions:** they put $112 into the cut lists, all of it in R4.
   - **Effect on M1:** excluding them from the year-2 total would move R1 from 3.06% to about 3.08% and R4 from 0.59% to 0.60%. Neither conclusion changes.

8. **Currency shown in US dollars (presentation change, made at the user's request after publication).** The source data is in British pounds. All amounts are now converted at one fixed rate, applied in the SQL staging step: $1.5774 per £1, the Federal Reserve's average daily rate over the data period (FRED series DEXUSUK) (509 business days, 2009-12-01 to 2011-12-09).
   - **Verification:** every share, count, interval, ranking and cut list is identical to the pound-based run, and every amount is exactly 1.5774 times its pound value.
   - **Why one rate:** monthly rates would have changed the shares slightly and broken comparability with the frozen plan.

## How the memo uses the results

The pre-specified decision criterion **H1 failed narrowly**: R1 puts 3.06% of year-2 revenue at risk, against the 3% guardrail, with a 95% interval of 2.66–3.49%. As the plan required, the memo therefore does **not** recommend R1, and it states that the class-C tail is not safe to cut on revenue alone.

The memo does recommend R4, the pre-specified key-account variant, which puts 0.59% at risk (95% CI 0.50–0.69%). This is a choice made after seeing all four rules' year-2 results, so it carries some selection risk. Two things limit it:
- R4 was specified before any year-2 result was computed.
- Its interval sits far below the guardrail.

The memo says this explicitly.
