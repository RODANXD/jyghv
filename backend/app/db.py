"""SQLite access. The DB is a committed snapshot, loaded once into memory."""
from __future__ import annotations

import sqlite3
from functools import lru_cache

import pandas as pd

from .config import DB_PATH


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (actuals, forecasts) with UTC-aware timestamps."""
    with sqlite3.connect(DB_PATH) as con:
        act = pd.read_sql("SELECT startTime, generation FROM actuals", con)
        fc = pd.read_sql("SELECT startTime, publishTime, generation FROM forecasts", con)
    for df in (act, fc):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    return act, fc
