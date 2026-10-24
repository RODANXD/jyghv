import pandas as pd
import pytest

from app.metrics import summarize


def test_hand_checked_metrics():
    df = pd.DataFrame({"forecast": [1000.0, 2000.0, 3000.0, 4000.0],
                       "actual": [900.0, 2100.0, 2700.0, 4000.0]})
    df["error"] = df["actual"] - df["forecast"]  # -100, 100, -300, 0
    m = summarize(df)
    assert m["bias_mw"] == pytest.approx(-75.0)
    assert m["mae_mw"] == pytest.approx(125.0)
    assert m["rmse_mw"] == pytest.approx((110000 / 4) ** 0.5)
    assert m["shortfall_p90_mw"] > 0


def test_empty_input():
    assert summarize(pd.DataFrame(columns=["forecast", "actual", "error"])) == {"n": 0}
