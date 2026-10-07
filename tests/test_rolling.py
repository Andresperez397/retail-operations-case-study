from __future__ import annotations

import pandas as pd
import pytest

from retail import rolling
from retail.db import staged
from tests.test_staging_and_kpis import ROWS


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    path = tmp_path_factory.mktemp("raw") / "raw.parquet"
    pd.DataFrame(ROWS).to_parquet(path, index=False)
    return staged(path)


def test_origin_windows_never_overlap_and_use_the_right_lengths():
    o = rolling.Origin(pd.Timestamp("2010-12-01"))
    assert o.train_start == pd.Timestamp("2009-12-01") and o.test_end == pd.Timestamp("2011-06-01")
    early = rolling.Origin(pd.Timestamp("2010-06-01"))
    assert early.train_start == pd.Timestamp("2009-12-01")  # only six months of history exist
    assert early.new_launch_from == pd.Timestamp("2010-03-01")


def test_window_products_partition_the_data_by_date(con):
    a = rolling.window_products(con, pd.Timestamp("2010-01-01"), pd.Timestamp("2010-12-01"))
    b = rolling.window_products(con, pd.Timestamp("2010-12-01"), pd.Timestamp("2011-06-30"))
    whole = rolling.window_products(con, pd.Timestamp("2010-01-01"), pd.Timestamp("2011-06-30"))
    assert a["net_revenue"].sum() + b["net_revenue"].sum() == pytest.approx(whole["net_revenue"].sum())


def test_nothing_after_the_cutoff_leaks_into_the_training_window(con):
    train = rolling.window_products(con, pd.Timestamp("2010-01-01"), pd.Timestamp("2010-12-01"))
    assert train["first_sale"].max() < pd.Timestamp("2010-12-01")
