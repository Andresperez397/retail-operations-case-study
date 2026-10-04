"""Download the UCI Online Retail II dataset, verify it, and convert both Excel sheets to one text-typed Parquet file.

    python scripts/fetch_data.py

Source: Chen, D. (2019). Online Retail II [Dataset]. UCI Machine Learning Repository.
https://doi.org/10.24432/C5CG6D (CC BY 4.0). About 45 MB.
Every value is read as text, so nothing is coerced before the SQL staging layer sees it.
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

URL = "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip"
SHA256 = "572e36277c2390fbfde10664750731e0a86f55e33470d91919085f0408e67bfb"
RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    zpath = RAW / "online_retail_ii.zip"
    if not zpath.exists():
        print("downloading", URL)
        urllib.request.urlretrieve(URL, zpath)
    digest = hashlib.sha256(zpath.read_bytes()).hexdigest()
    if digest != SHA256:
        print(f"checksum differs from the file used for this analysis ({digest}); results may differ")
    with zipfile.ZipFile(zpath) as z:
        z.extractall(RAW)
    sheets = pd.read_excel(RAW / "online_retail_II.xlsx", sheet_name=None, dtype=str)
    df = pd.concat([s.assign(sheet=name) for name, s in sheets.items()], ignore_index=True)
    df.to_parquet(RAW / "online_retail_ii_text.parquet", index=False)
    print(f"{len(df):,} rows from {len(sheets)} sheets -> data/raw/online_retail_ii_text.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
