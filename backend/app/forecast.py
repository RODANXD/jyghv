"""Decision-time forecast selection: the core business logic.

Rule: for each target half-hour (startTime), the forecast available at decision
time is the row with the greatest publishTime that is <= the cutoff.
Pure functions, no I/O, so they are easy to test.
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

import pandas as pd


def cutoff_for_delivery(delivery_date: date, cutoff_time: time, days_before: int = 1) -> datetime:
    """Cutoff instant (UTC) for a delivery day, e.g. 09:00 on D-1."""
    d = delivery_date - timedelta(days=days_before)
    return datetime.combine(d, cutoff_time, tzinfo=timezone.utc)


def select_latest_before_cutoff(forecasts: pd.DataFrame, cutoff: datetime) -> pd.DataFrame:
    """Latest forecast per startTime with publishTime <= cutoff.

    Input columns: startTime, publishTime, generation (tz-aware UTC timestamps).
    Output: one row per startTime. Targets with no eligible forecast are absent.
    """
    eligible = forecasts[forecasts["publishTime"] <= pd.Timestamp(cutoff)]
    return (
        eligible.sort_values(["startTime", "publishTime"])
        .drop_duplicates(subset="startTime", keep="last")
        .reset_index(drop=True)
    )


def decision_dataset(
    forecasts: pd.DataFrame,
    actuals: pd.DataFrame,
    delivery_dates: list[date],
    cutoff_time: time,
    days_before: int = 1,
) -> pd.DataFrame:
    """Decision-time forecast joined with actuals for the given delivery days.

    Each delivery day uses its own cutoff. Returns columns:
    startTime, publishTime, forecast, actual, error (actual - forecast), delivery_date.
    """
    parts = []
    for d in delivery_dates:
        cutoff = cutoff_for_delivery(d, cutoff_time, days_before)
        day_start = pd.Timestamp(datetime.combine(d, time(0, 0), tzinfo=timezone.utc))
        day_end = day_start + pd.Timedelta(days=1)
        day_fc = forecasts[(forecasts["startTime"] >= day_start) & (forecasts["startTime"] < day_end)]
        sel = select_latest_before_cutoff(day_fc, cutoff)
        sel["delivery_date"] = d
        parts.append(sel)
    if not parts:
        return pd.DataFrame(columns=["startTime", "publishTime", "forecast", "actual", "error", "delivery_date"])
    fc = pd.concat(parts, ignore_index=True).rename(columns={"generation": "forecast"})
    act = actuals.rename(columns={"generation": "actual"})[["startTime", "actual"]]
    out = fc.merge(act, on="startTime", how="left")
    out["error"] = out["actual"] - out["forecast"]
    return out
