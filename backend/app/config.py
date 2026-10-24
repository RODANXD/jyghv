"""Central configuration. Every business assumption lives here, in one place."""
from datetime import time
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "elexon.db"
STATIC_DIR = Path(__file__).resolve().parents[1] / "static"

# --- Business assumptions (state these in the README and the video) ---------
# UK in January is on GMT (= UTC), so no daylight-saving edge cases in scope.
DEFAULT_CUTOFF_TIME = time(9, 0)   # day-ahead gate closure assumed 09:00 on D-1
DEFAULT_DAYS_BEFORE = 1            # decision is made 1 day before delivery

# "Decisions made in January 2026" => cutoffs on 1-31 Jan => deliveries 2 Jan - 1 Feb.
DECISION_START = "2026-01-01"
DECISION_END = "2026-01-31"
DELIVERY_START = "2026-01-02"
DELIVERY_END = "2026-02-01"

# Only keep forecasts made up to this many hours before delivery (keeps DB small).
MAX_HORIZON_HOURS = 72

ELEXON_BASE = "https://data.elexon.co.uk/bmrs/api/v1"
