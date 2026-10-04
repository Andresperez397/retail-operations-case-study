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
   - The largest single false cuts are low-volume year-1 products that grew in year 2. For example, a rosette went from £413 to £3,605, and two pet bowls each went from about £500 to about £2,600.
4. **Natural attrition:** 927 of the 4,073 year-1 products did not sell at all in year 2, and 651 products sold in year 2 that had not sold in year 1. The retailer was already turning over about a fifth of its range each year without a formal rule.
5. **R4 list detail:**
   - 906 products, 22% of the year-1 range
   - £83.7k of year-1 net revenue (0.9%) and £55.3k of year-2 net revenue (0.6%)
   - 368 of the 906 had no year-2 sales.

6. **One order explains year 2's higher cancellation rate.** The year-2 cancellation rate (3.1%, against 2.6% in year 1) includes a single order for 74,215 storage jars (£77k), cancelled 16 minutes after it was placed. Without that pair, year 2 is 2.35%, below year 1's 2.56%. The KPI definition is unchanged; the README and dashboard now report both figures so the change is not read as a trend. The decision analyses are unaffected: the cancellation-persistence test counts lines, not value.
7. **Price outliers.** 92 sale lines are priced more than 20 times their product's median price: 73 lines worth £4.6k in year 1 and 19 worth £39.8k in year 2. The largest is 60 wicker baskets at £649.50 each, against a usual £5.95. These look like entry errors but are kept, because the plan did not provide for removing them.
   - **Effect on the decisions:** they put £71 into the cut lists, all of it in R4.
   - **Effect on M1:** excluding them from the year-2 total would move R1 from 3.06% to about 3.08% and R4 from 0.59% to 0.60%. Neither conclusion changes.

## How the memo uses the results

The pre-specified decision criterion **H1 failed narrowly**: R1 puts 3.06% of year-2 revenue at risk, against the 3% guardrail, with a 95% interval of 2.66–3.49%. As the plan required, the memo therefore does **not** recommend R1, and it states that the class-C tail is not safe to cut on revenue alone.

The memo does recommend R4, the pre-specified key-account variant, which puts 0.59% at risk (95% CI 0.50–0.69%). This is a choice made after seeing all four rules' year-2 results, so it carries some selection risk. Two things limit it:
- R4 was specified before any year-2 result was computed.
- Its interval sits far below the guardrail.

The memo says this explicitly.
