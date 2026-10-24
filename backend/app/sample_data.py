"""Generate SYNTHETIC data in the same schema as ingest.py, for UI development only.
Run: python -m app.sample_data   (overwrites data/elexon.db; re-run app.ingest for real data)
"""
import sqlite3

import numpy as np
import pandas as pd

from .config import DB_PATH

rng = np.random.default_rng(7)
idx = pd.date_range("2026-01-01", "2026-02-02", freq="30min", inclusive="left", tz="UTC")
base = 7000 + 4000 * np.sin(np.arange(len(idx)) / 120) + rng.normal(0, 300, len(idx)).cumsum() * 0.1
actual = np.clip(base, 200, 14000)
act = pd.DataFrame({"startTime": idx, "generation": actual})
rows = []
for t, a in zip(idx, actual):
    for h in range(1, 73, 3):
        pub = t - pd.Timedelta(hours=h)
        rows.append((t, pub, max(0, a + rng.normal(0, 150 + 25 * h) - 80)))
fc = pd.DataFrame(rows, columns=["startTime", "publishTime", "generation"])
with sqlite3.connect(DB_PATH) as con:
    for name, df in (("actuals", act), ("forecasts", fc)):
        out = df.copy()
        for c in out.columns:
            if "Time" in c:
                out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        out.to_sql(name, con, if_exists="replace", index=False)
print("sample data written")
