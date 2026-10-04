-- Product-by-window aggregates used by the range analysis and the dashboard.
-- Input: view `product_lines` (sensitivity check S1 substitutes a source that keeps exact duplicates).
-- Output: table `product_year`.
CREATE OR REPLACE TABLE product_year AS
SELECT
    stock_code,
    analysis_year,
    any_value(description ORDER BY invoice_ts DESC) FILTER (WHERE line_type = 'sale') AS description,
    sum(line_value) AS net_revenue,
    coalesce(sum(line_value) FILTER (WHERE line_type = 'sale'), 0) AS gross_sales,
    count(*) FILTER (WHERE line_type = 'sale') AS sale_lines,
    count(*) FILTER (WHERE line_type = 'cancellation') AS cancel_lines,
    count(DISTINCT invoice) FILTER (WHERE line_type = 'sale') AS orders,
    count(DISTINCT customer_id) FILTER (WHERE line_type = 'sale') AS customers,
    min(invoice_ts) FILTER (WHERE line_type = 'sale') AS first_sale
FROM product_lines
WHERE analysis_year IN ('Y1', 'Y2')
GROUP BY 1, 2;
