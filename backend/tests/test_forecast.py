from datetime import date, datetime, time, timezone

import pandas as pd

from app.forecast import cutoff_for_delivery, decision_dataset, select_latest_before_cutoff


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def fc_frame():
    return pd.DataFrame({
        "startTime": [ts("2026-01-10 12:00")] * 3,
        "publishTime": [ts("2026-01-09 06:00"), ts("2026-01-09 08:00"), ts("2026-01-09 10:00")],
        "generation": [1000.0, 1200.0, 1500.0],
    })


def test_cutoff_is_previous_day():
    c = cutoff_for_delivery(date(2026, 1, 10), time(9, 0))
    assert c == datetime(2026, 1, 9, 9, 0, tzinfo=timezone.utc)


def test_picks_latest_publish_before_cutoff():
    out = select_latest_before_cutoff(fc_frame(), datetime(2026, 1, 9, 9, 0, tzinfo=timezone.utc))
    assert len(out) == 1 and out.iloc[0]["generation"] == 1200.0


def test_publish_exactly_at_cutoff_is_included():
    out = select_latest_before_cutoff(fc_frame(), datetime(2026, 1, 9, 10, 0, tzinfo=timezone.utc))
    assert out.iloc[0]["generation"] == 1500.0


def test_no_eligible_forecast_gives_empty():
    out = select_latest_before_cutoff(fc_frame(), datetime(2026, 1, 9, 5, 0, tzinfo=timezone.utc))
    assert out.empty


def test_decision_dataset_error_sign():
    act = pd.DataFrame({"startTime": [ts("2026-01-10 12:00")], "generation": [1000.0]})
    df = decision_dataset(fc_frame(), act, [date(2026, 1, 10)], time(9, 0))
    assert df.iloc[0]["forecast"] == 1200.0 and df.iloc[0]["error"] == -200.0
