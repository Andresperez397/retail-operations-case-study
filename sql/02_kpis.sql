-- KPI layer: one row per month and one per analysis window, with identical definitions (see KPI_DEFINITIONS.md).
-- Input: view `product_lines` from 01_staging.sql. Output: table `kpis`.

CREATE OR REPLACE TABLE customer_first_month AS
SELECT customer_id, min(date_trunc('month', invoice_ts))::DATE AS first_month
FROM product_lines
WHERE line_type = 'sale' AND customer_id IS NOT NULL
GROUP BY 1;

CREATE OR REPLACE TABLE kpi_base AS
SELECT p.*,
       date_trunc('month', p.invoice_ts)::DATE AS month,
       f.first_month
FROM product_lines p
LEFT JOIN customer_first_month f USING (customer_id);

CREATE OR REPLACE TABLE kpis AS
WITH periods AS (
    SELECT 'month' AS period_type, strftime(month, '%Y-%m') AS period, month AS period_start, * FROM kpi_base
    UNION ALL
    SELECT 'window' AS period_type, analysis_year AS period,
           CASE analysis_year WHEN 'Y1' THEN DATE '2009-12-01' WHEN 'Y2' THEN DATE '2010-12-01'
                ELSE DATE '2011-12-01' END AS period_start,
           * FROM kpi_base
)
SELECT
    period_type,
    period,
    sum(line_value) FILTER (WHERE line_type = 'sale') AS gross_sales,
    -coalesce(sum(line_value) FILTER (WHERE line_type = 'cancellation'), 0) AS cancelled_value,
    sum(line_value) AS net_revenue,
    count(DISTINCT invoice) FILTER (WHERE line_type = 'sale') AS orders,
    gross_sales / orders AS average_order_value,
    cancelled_value / gross_sales AS cancellation_rate,
    count(DISTINCT customer_id) FILTER (WHERE line_type = 'sale') AS active_customers,
    -- A customer is new in the period of their first purchase; returning customers first bought before it.
    -- The data starts in December 2009, so every customer active then (and all of year 1) looks new.
    count(DISTINCT customer_id) FILTER (WHERE line_type = 'sale' AND first_month >= period_start) AS new_customers,
    coalesce(sum(line_value) FILTER (WHERE line_type = 'sale' AND customer_id IS NOT NULL AND first_month < period_start), 0)
        / sum(line_value) FILTER (WHERE line_type = 'sale' AND customer_id IS NOT NULL) AS returning_customer_share,
    sum(line_value) FILTER (WHERE line_type = 'sale' AND customer_id IS NULL) / gross_sales AS sales_without_customer_id,
    sum(line_value) FILTER (WHERE line_type = 'sale' AND country <> 'United Kingdom') / gross_sales
        AS international_share,
    count(DISTINCT stock_code) FILTER (WHERE line_type = 'sale') AS products_sold,
    count(*) FILTER (WHERE line_type = 'sale') AS sale_lines
FROM periods
GROUP BY ALL
ORDER BY period_type, period;
