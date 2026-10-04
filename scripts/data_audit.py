"""Data audit: structural checks on the raw extract and counts at every staging step.

    PYTHONPATH=src python scripts/data_audit.py

Run before the analysis plan was frozen. It reports only data-structure facts and whole-dataset totals by
analysis window; no product-level results for year 2 are computed here.
"""

from __future__ import annotations

import json

from retail.db import ROOT, staged

OUT = ROOT / "reports" / "tables" / "data_audit.json"


def main() -> None:
    con = staged()

    def one(sql: str):
        return con.execute(sql).fetchone()

    def rows(sql: str) -> list[dict]:
        df = con.execute(sql).fetchdf()
        return df.astype(object).where(df.notna(), None).to_dict(orient="records")

    a: dict = {}
    a["raw_rows_by_sheet"] = rows(
        "SELECT sheet, count(*) AS n, min(invoice_ts)::VARCHAR AS first_line, max(invoice_ts)::VARCHAR AS last_line "
        "FROM typed GROUP BY 1 ORDER BY 1"
    )
    # The overlap rows must be exact copies of 2009-2010 sheet rows, or dropping them would lose data.
    a["sheet_overlap"] = dict(
        zip(
            ["rows_in_2010_2011_sheet", "rows_in_2009_2010_sheet_same_window", "identical_rows"],
            one("""WITH a AS (SELECT invoice, stock_code, description, quantity, invoice_ts, price, customer_id, country
                              FROM typed WHERE sheet = 'Year 2009-2010' AND invoice_ts >= TIMESTAMP '2010-12-01'),
                        b AS (SELECT invoice, stock_code, description, quantity, invoice_ts, price, customer_id, country
                              FROM typed WHERE sheet = 'Year 2010-2011' AND invoice_ts < TIMESTAMP '2010-12-10')
                   SELECT (SELECT count(*) FROM b), (SELECT count(*) FROM a),
                          (SELECT count(*) FROM (SELECT * FROM a INTERSECT ALL SELECT * FROM b))"""),
            strict=True,
        )
    )
    a["row_status"] = rows("SELECT row_status, count(*) AS n FROM lines GROUP BY 1 ORDER BY 2 DESC")
    a["line_types_kept"] = rows(
        "SELECT line_type, count(*) AS n, round(sum(line_value), 2) AS value FROM lines WHERE row_status = 'kept' "
        "GROUP BY 1 ORDER BY 2 DESC"
    )
    a["non_product_codes"] = rows(
        "SELECT stock_code, any_value(description ORDER BY row_id) AS example_description, count(*) AS n, "
        "round(sum(line_value), 2) AS value FROM lines WHERE row_status = 'kept' AND line_type = 'non_product' "
        "GROUP BY 1 ORDER BY 3 DESC"
    )
    a["stock_adjustment_descriptions"] = rows(
        "SELECT coalesce(description, '(blank)') AS description, count(*) AS n FROM lines "
        "WHERE row_status = 'kept' AND line_type = 'stock_adjustment' GROUP BY 1 ORDER BY 2 DESC LIMIT 10"
    )
    a["lowercase_stock_codes_in_raw"] = one("SELECT count(*) FROM raw WHERE StockCode <> upper(StockCode)")[0]
    a["codes_with_several_descriptions"] = one(
        "SELECT count(*) FROM (SELECT stock_code FROM lines WHERE row_status = 'kept' AND line_type = 'sale' "
        "GROUP BY 1 HAVING count(DISTINCT description) > 1)"
    )[0]
    a["missing_customer_id"] = dict(
        zip(
            ["sale_lines", "sale_lines_without_id", "share_of_sales_value_without_id"],
            one(
                "SELECT count(*), count(*) FILTER (WHERE customer_id IS NULL), "
                "sum(line_value) FILTER (WHERE customer_id IS NULL) / sum(line_value) "
                "FROM product_lines WHERE line_type = 'sale'"
            ),
            strict=True,
        )
    )
    a["largest_lines"] = rows(
        "SELECT invoice, stock_code, description, quantity, price, invoice_ts::VARCHAR AS invoice_ts "
        "FROM product_lines ORDER BY abs(quantity) DESC LIMIT 4"
    )
    a["windows"] = rows(
        "SELECT analysis_year, count(*) AS lines, count(DISTINCT invoice) FILTER (WHERE line_type = 'sale') AS orders, "
        "count(DISTINCT stock_code) FILTER (WHERE line_type = 'sale') AS products_sold, "
        "count(DISTINCT customer_id) AS customers, round(sum(line_value), 0) AS net_product_revenue "
        "FROM product_lines GROUP BY 1 ORDER BY 1"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(a, indent=2, default=str))
    print(json.dumps(a, indent=2, default=str))


if __name__ == "__main__":
    main()
