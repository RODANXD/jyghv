"""Download Elexon FUELHH (WIND) and WINDFOR for the challenge window into SQLite.

Run once from your machine:  python -m app.ingest
Then commit backend/data/elexon.db so the deployed app never calls Elexon live.
NOTE: verify parameter names against the Elexon docs if a request returns 400.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests

from .config import DB_PATH, DELIVERY_END, DELIVERY_START, ELEXON_BASE, MAX_HORIZON_HOURS


def _get(path: str, params: dict) -> list[dict]:
    r = requests.get(f"{ELEXON_BASE}{path}", params={**params, "format": "json"}, timeout=120)
    r.raise_for_status()
    body = r.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def _chunks(start: datetime, end: datetime, days: int):
    cur = start
    while cur < end:
        nxt = min(cur + timedelta(days=days), end)
        yield cur, nxt
        cur = nxt


def fetch_actuals(start: datetime, end: datetime) -> pd.DataFrame:
    rows: list[dict] = []
    for a, b in _chunks(start, end, 7):
        rows += _get(
            "/datasets/FUELHH/stream",
            {"settlementDateFrom": a.date().isoformat(), "settlementDateTo": b.date().isoformat(), "fuelType": "WIND"},
        )
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"][["startTime", "generation"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df.drop_duplicates("startTime").sort_values("startTime")


def fetch_forecasts(start: datetime, end: datetime) -> pd.DataFrame:
    """Forecasts *published* from (start - 4 days) to end, trimmed to the horizon cap."""
    rows: list[dict] = []
    for a, b in _chunks(start - timedelta(days=4), end, 2):
        rows += _get(
            "/datasets/WINDFOR/stream",
            {"publishDateTimeFrom": a.strftime("%Y-%m-%dT%H:%MZ"), "publishDateTimeTo": b.strftime("%Y-%m-%dT%H:%MZ")},
        )
    df = pd.DataFrame(rows)[["startTime", "publishTime", "generation"]]
    for c in ("startTime", "publishTime"):
        df[c] = pd.to_datetime(df[c], utc=True)
    df = df[(df["startTime"] >= pd.Timestamp(start)) & (df["startTime"] < pd.Timestamp(end))]
    horizon_h = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    df = df[(horizon_h >= 0) & (horizon_h <= MAX_HORIZON_HOURS)]
    return df.drop_duplicates(["startTime", "publishTime"]).sort_values(["startTime", "publishTime"])


def main() -> None:
    start = datetime.fromisoformat(DELIVERY_START).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(DELIVERY_END).replace(tzinfo=timezone.utc) + timedelta(days=1)
    act, fc = fetch_actuals(start, end), fetch_forecasts(start, end)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as con:
        for name, df in (("actuals", act), ("forecasts", fc)):
            out = df.copy()
            for c in out.columns:
                if "Time" in c:
                    out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            out.to_sql(name, con, if_exists="replace", index=False)
    print(f"actuals: {len(act)} rows, forecasts: {len(fc)} rows -> {DB_PATH}")


if __name__ == "__main__":
    main()
