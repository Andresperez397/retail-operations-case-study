-- Staging: one typed, de-duplicated table of invoice lines, each with a line type and an analysis window.
-- Input: table `raw` (every column text, as delivered in the two Excel sheets).
-- Output: table `lines`. Every row of `raw` is kept with a status, so each exclusion can be counted.

-- 1. Type every column. Stock codes are upper-cased: '85123a' and '85123A' are the same product.
--    Prices arrive in British pounds; `price` is converted to US dollars at one fixed rate (macro usd_per_gbp(),
--    defined in src/retail/currency.py), and the original is kept as `price_gbp`.
CREATE OR REPLACE TABLE typed AS
SELECT
    row_number() OVER () AS row_id,
    sheet,
    trim(Invoice) AS invoice,
    upper(trim(StockCode)) AS stock_code,
    trim(Description) AS description,
    CAST(Quantity AS INTEGER) AS quantity,
    CAST(InvoiceDate AS TIMESTAMP) AS invoice_ts,
    CAST(Price AS DOUBLE) AS price_gbp,
    CAST(Price AS DOUBLE) * usd_per_gbp() AS price,
    NULLIF(trim("Customer ID"), '') AS customer_id,
    trim(Country) AS country
FROM raw;

-- 2. Flag rows to drop.
--    a. The two sheets overlap: the 2010-2011 sheet repeats every line from 1-9 December 2010, which the
--       2009-2010 sheet already holds (the audit checks that the repeated rows are identical).
--    b. Exact duplicate lines (same invoice, product, description, quantity, time, price and customer) keep
--       their first copy only.
CREATE OR REPLACE TABLE flagged AS
SELECT *,
    sheet = 'Year 2010-2011' AND invoice_ts < TIMESTAMP '2010-12-10' AS is_sheet_overlap,
    row_number() OVER (
        PARTITION BY invoice, stock_code, description, quantity, invoice_ts, price, customer_id, country
        ORDER BY row_id
    ) > 1 AS is_exact_duplicate
FROM typed;

-- 3. Classify each line. Non-product codes are postage, fees, manual entries, adjustments, test products
--    and gift vouchers: they are not part of the product catalogue, whatever their invoice type.
CREATE OR REPLACE TABLE lines AS
SELECT *,
    CASE
        WHEN is_sheet_overlap THEN 'dropped: sheet overlap'
        WHEN is_exact_duplicate THEN 'dropped: exact duplicate'
        ELSE 'kept'
    END AS row_status,
    CASE
        WHEN stock_code IN ('POST', 'DOT', 'C2', 'M', 'D', 'S', 'B', 'BANK CHARGES', 'ADJUST', 'ADJUST2',
                            'AMAZONFEE', 'CRUK', 'TEST001', 'TEST002')
             OR stock_code LIKE 'GIFT%' THEN 'non_product'
        WHEN invoice LIKE 'C%' THEN 'cancellation'
        WHEN invoice LIKE 'A%' THEN 'bad_debt_adjustment'
        WHEN quantity < 0 THEN 'stock_adjustment'
        WHEN price = 0 THEN 'zero_price'
        ELSE 'sale'
    END AS line_type,
    -- Cancellations carry negative quantities; abs() keeps the one positive-quantity cancellation negative too.
    CASE
        WHEN invoice LIKE 'C%' THEN -abs(quantity) * price
        ELSE quantity * price
    END AS line_value,
    CASE
        WHEN invoice_ts >= TIMESTAMP '2009-12-01' AND invoice_ts < TIMESTAMP '2010-12-01' THEN 'Y1'
        WHEN invoice_ts >= TIMESTAMP '2010-12-01' AND invoice_ts < TIMESTAMP '2011-12-01' THEN 'Y2'
        ELSE 'Dec 2011 (partial)'
    END AS analysis_year
FROM flagged;

-- 4. The analysis table: kept product lines that move revenue (sales and their cancellations).
CREATE OR REPLACE VIEW product_lines AS
SELECT row_id, invoice, stock_code, description, quantity, invoice_ts, price, customer_id, country,
       line_type, line_value, analysis_year
FROM lines
WHERE row_status = 'kept' AND line_type IN ('sale', 'cancellation');
