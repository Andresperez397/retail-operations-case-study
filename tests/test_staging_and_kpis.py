"""SQL staging and KPI layer on a tiny synthetic extract with every audited problem planted."""

from __future__ import annotations

import pandas as pd
import pytest

from retail.currency import USD_PER_GBP
from retail.db import run_sql, staged

S1, S2 = "Year 2009-2010", "Year 2010-2011"


def row(inv, code, qty, ts, price, cust, sheet=S1, desc="ITEM", country="United Kingdom"):
    return {"Invoice": inv, "StockCode": code, "Description": desc, "Quantity": str(qty), "InvoiceDate": ts,
            "Price": str(price), "Customer ID": cust, "Country": country, "sheet": sheet}  # fmt: skip


ROWS = [
    row("100001", "85123A", 10, "2010-01-05 10:00:00", 2.5, "12345"),  # sale, Y1
    row("100001", "85123A", 10, "2010-01-05 10:00:00", 2.5, "12345"),  # exact duplicate -> dropped
    row("100002", "85123a", 4, "2010-02-01 09:00:00", 2.5, None),  # lower-case code, no customer ID
    row("C100003", "85123A", -2, "2010-02-03 09:00:00", 2.5, "12345"),  # cancellation
    row("C100004", "22423", 1, "2010-03-01 09:00:00", 10.0, "12345"),  # positive-quantity cancellation
    row("100005", "POST", 1, "2010-03-02 09:00:00", 18.0, "12345"),  # postage: non-product
    row("100006", "22423", -5, "2010-03-03 09:00:00", 0.0, None, desc="damaged"),  # stock adjustment
    row("100007", "22423", 3, "2010-03-04 09:00:00", 0.0, "12345"),  # zero price
    row("A100008", "B", 1, "2010-03-05 09:00:00", -500.0, None),  # bad-debt adjustment (non-product code)
    row("100009", "22423", 2, "2010-12-05 09:00:00", 10.0, "67890"),  # Y2 sale in the 2009-2010 sheet
    row("100009", "22423", 2, "2010-12-05 09:00:00", 10.0, "67890", sheet=S2),  # sheet overlap -> dropped
    row("100010", "22423", 1, "2011-06-01 09:00:00", 10.0, "12345", sheet=S2, country="France"),  # Y2 sale
    row("100011", "22423", 1, "2011-12-02 09:00:00", 10.0, "67890", sheet=S2),  # December 2011
]


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    path = tmp_path_factory.mktemp("raw") / "raw.parquet"
    pd.DataFrame(ROWS).to_parquet(path, index=False)
    c = staged(path)
    run_sql(c, "02_kpis.sql")
    return c


def status(con, invoice):
    return con.execute(
        "SELECT row_status, line_type FROM lines WHERE invoice = ? ORDER BY row_id", [invoice]
    ).fetchall()


def test_sheet_overlap_and_duplicates_are_dropped_not_lost(con):
    assert status(con, "100009") == [("kept", "sale"), ("dropped: sheet overlap", "sale")]
    assert status(con, "100001") == [("kept", "sale"), ("dropped: exact duplicate", "sale")]
    assert con.execute("SELECT count(*) FROM lines").fetchone()[0] == len(ROWS)


def test_line_types(con):
    assert status(con, "100005") == [("kept", "non_product")]
    assert status(con, "100006") == [("kept", "stock_adjustment")]
    assert status(con, "100007") == [("kept", "zero_price")]
    assert status(con, "A100008") == [("kept", "non_product")]
    assert status(con, "C100003") == [("kept", "cancellation")]


def test_codes_upper_cased_and_cancellations_negative(con):
    codes = {r[0] for r in con.execute("SELECT stock_code FROM product_lines").fetchall()}
    assert codes == {"85123A", "22423"}
    v = dict(con.execute("SELECT invoice, line_value FROM product_lines WHERE line_type = 'cancellation'").fetchall())
    assert v == pytest.approx({"C100003": -5.0 * USD_PER_GBP, "C100004": -10.0 * USD_PER_GBP})


def test_prices_converted_to_dollars_with_original_kept(con):
    p = con.execute("SELECT price_gbp, price FROM typed WHERE invoice = '100001' LIMIT 1").fetchone()
    assert p[0] == 2.5 and p[1] == pytest.approx(2.5 * USD_PER_GBP)


def test_windows(con):
    w = dict(con.execute("SELECT invoice, analysis_year FROM product_lines").fetchall())
    assert w["100001"] == "Y1" and w["100009"] == "Y2" and w["100011"] == "Dec 2011 (partial)"


def test_window_kpis(con):
    k = con.execute("SELECT * FROM kpis WHERE period_type = 'window' AND period = 'Y1'").fetchdf().iloc[0]
    assert k["gross_sales"] == pytest.approx(35.0 * USD_PER_GBP)  # £25 + £10 (duplicate dropped), in dollars
    assert k["cancelled_value"] == pytest.approx(15.0 * USD_PER_GBP)
    assert k["net_revenue"] == pytest.approx(20.0 * USD_PER_GBP)
    assert k["orders"] == 2
    assert k["active_customers"] == 1
    assert k["sales_without_customer_id"] == pytest.approx(10.0 / 35.0)
    y2 = con.execute("SELECT * FROM kpis WHERE period_type = 'window' AND period = 'Y2'").fetchdf().iloc[0]
    assert y2["new_customers"] == 1  # 67890 first bought in Y2; 12345 is returning
    assert y2["returning_customer_share"] == pytest.approx(10.0 / 30.0)
    assert y2["international_share"] == pytest.approx(10.0 / 30.0)


def test_monthly_new_customers(con):
    m = dict(con.execute("SELECT period, new_customers FROM kpis WHERE period_type = 'month'").fetchall())
    assert m["2010-01"] == 1 and m["2010-02"] == 0 and m["2010-12"] == 1 and m["2011-06"] == 0
