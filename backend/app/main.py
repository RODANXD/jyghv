"""FastAPI app: JSON API under /api, built React app served from /."""
from __future__ import annotations

from datetime import date, time, timedelta

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import db, metrics
from .config import (DEFAULT_CUTOFF_TIME, DEFAULT_DAYS_BEFORE, DELIVERY_END, DELIVERY_START, STATIC_DIR)
from .forecast import cutoff_for_delivery, decision_dataset

app = FastAPI(title="Wind forecast decision support")


def _days(start: date, end: date) -> list[date]:
    if end < start:
        raise HTTPException(400, "end must be on or after start")
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def _ts(x) -> str | None:
    return None if x is None or x != x else x.strftime("%Y-%m-%dT%H:%M:%SZ")


@app.get("/api/meta")
def meta() -> dict:
    return {
        "delivery_start": DELIVERY_START,
        "delivery_end": DELIVERY_END,
        "default_cutoff_time": DEFAULT_CUTOFF_TIME.strftime("%H:%M"),
        "default_days_before": DEFAULT_DAYS_BEFORE,
    }


@app.get("/api/forecast")
def forecast(
    delivery_date: date,
    cutoff_time: time = DEFAULT_CUTOFF_TIME,
    days_before: int = Query(DEFAULT_DAYS_BEFORE, ge=0, le=3),
) -> dict:
    act, fc = db.load()
    df = decision_dataset(fc, act, [delivery_date], cutoff_time, days_before)
    if df.empty:
        raise HTTPException(404, "No forecast available before that cutoff")
    points = [
        {"startTime": _ts(r.startTime), "publishTime": _ts(r.publishTime),
         "forecast": r.forecast, "actual": None if r.actual != r.actual else r.actual}
        for r in df.itertuples()
    ]
    return {
        "delivery_date": delivery_date.isoformat(),
        "cutoff": cutoff_for_delivery(delivery_date, cutoff_time, days_before).isoformat(),
        "metrics": metrics.summarize(df),
        "points": points,
    }


@app.get("/api/metrics")
def get_metrics(
    start: date,
    end: date,
    cutoff_time: time = DEFAULT_CUTOFF_TIME,
    days_before: int = Query(DEFAULT_DAYS_BEFORE, ge=0, le=3),
) -> dict:
    act, fc = db.load()
    df = decision_dataset(fc, act, _days(start, end), cutoff_time, days_before)
    return {
        "summary": metrics.summarize(df),
        "daily": metrics.daily(df),
        "by_hour": metrics.by_hour(df),
        "by_wind_level": metrics.by_wind_level(df),
    }


@app.get("/api/metrics/by-horizon")
def by_horizon(bucket_hours: int = Query(6, ge=1, le=24)) -> list[dict]:
    act, fc = db.load()
    return metrics.by_horizon(fc, act, bucket_hours)


if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str) -> FileResponse:
        f = STATIC_DIR / path
        return FileResponse(f if path and f.is_file() else STATIC_DIR / "index.html")
