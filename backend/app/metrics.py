"""Error metrics. Convention: error = actual - forecast.

Negative error => wind under-delivered => buyer must cover the shortfall.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def summarize(df: pd.DataFrame) -> dict:
    """Headline metrics for rows with columns forecast, actual, error."""
    d = df.dropna(subset=["forecast", "actual"])
    if d.empty:
        return {"n": 0}
    e = d["error"].to_numpy(dtype=float)
    mean_actual = float(d["actual"].mean())
    p10, p50, p90 = (float(np.percentile(e, q)) for q in (10, 50, 90))
    nonzero = d[d["actual"] > 100]  # MAPE is unstable near zero wind
    mape = float((nonzero["error"].abs() / nonzero["actual"]).mean() * 100) if len(nonzero) else None
    return {
        "n": int(len(d)),
        "bias_mw": float(e.mean()),
        "mae_mw": float(np.abs(e).mean()),
        "rmse_mw": float(np.sqrt((e**2).mean())),
        "mape_pct": mape,
        "nmae_pct": float(np.abs(e).mean() / mean_actual * 100) if mean_actual else None,
        "mean_actual_mw": mean_actual,
        "p10_error_mw": p10,
        "p50_error_mw": p50,
        "p90_error_mw": p90,
        # Plan for wind to be this many MW below forecast, 90% of the time.
        "shortfall_p90_mw": max(0.0, -p10),
    }


def by_hour(df: pd.DataFrame) -> list[dict]:
    d = df.dropna(subset=["error"]).copy()
    d["hour"] = d["startTime"].dt.hour
    g = d.groupby("hour")["error"]
    out = pd.DataFrame({"mae_mw": g.apply(lambda s: s.abs().mean()), "bias_mw": g.mean()}).reset_index()
    return out.to_dict("records")


def by_wind_level(df: pd.DataFrame) -> list[dict]:
    d = df.dropna(subset=["error"]).copy()
    bins = [0, 3000, 6000, 9000, 12000, 1e9]
    labels = ["<3 GW", "3-6 GW", "6-9 GW", "9-12 GW", ">12 GW"]
    d["level"] = pd.cut(d["forecast"], bins=bins, labels=labels, include_lowest=True)
    g = d.groupby("level", observed=True)["error"]
    out = pd.DataFrame({"n": g.size(), "mae_mw": g.apply(lambda s: s.abs().mean()), "bias_mw": g.mean()}).reset_index()
    out["level"] = out["level"].astype(str)
    return out.to_dict("records")


def daily(df: pd.DataFrame) -> list[dict]:
    d = df.dropna(subset=["error"])
    g = d.groupby("delivery_date")["error"]
    out = pd.DataFrame({"mae_mw": g.apply(lambda s: s.abs().mean()), "bias_mw": g.mean()}).reset_index()
    out["delivery_date"] = out["delivery_date"].astype(str)
    return out.to_dict("records")


def by_horizon(forecasts: pd.DataFrame, actuals: pd.DataFrame, bucket_hours: int = 6) -> list[dict]:
    """Error vs forecast horizon (startTime - publishTime), across all forecasts."""
    d = forecasts.merge(actuals.rename(columns={"generation": "actual"})[["startTime", "actual"]], on="startTime")
    d["horizon_h"] = (d["startTime"] - d["publishTime"]).dt.total_seconds() / 3600
    d = d[d["horizon_h"] >= 0].copy()
    d["error"] = d["actual"] - d["generation"]
    d["bucket"] = (d["horizon_h"] // bucket_hours * bucket_hours).astype(int)
    g = d.groupby("bucket")["error"]
    out = pd.DataFrame({"n": g.size(), "mae_mw": g.apply(lambda s: s.abs().mean()), "bias_mw": g.mean()}).reset_index()
    return out.to_dict("records")
