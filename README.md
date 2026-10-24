# Wind forecast decision support (REint challenge)

Web app for day-ahead power buyers: shows the wind forecast that was available at the buying
cutoff, compares it with actual wind, and quantifies the error so a safety margin can be planned.

**Live app:** <add Heroku/Vercel URL>  |  **AI tools used:** Claude (code scaffolding and review).

## Assumptions
- "Decisions made in January 2026" = cutoffs 1-31 Jan, so deliveries 2 Jan - 1 Feb 2026.
- Default cutoff 09:00 on D-1 (UK time = UTC in January); user-configurable in the UI.
- Forecast used = per `startTime`, the row with the greatest `publishTime` <= cutoff.
- Error = actual - forecast. Negative = wind fell short. Headline buffer = -P10 of error (P90 shortfall).
- Only forecasts made 0-72h ahead are stored (keeps the snapshot small).

## Layout
- `backend/app/forecast.py` - cutoff + latest-forecast logic (pure, tested)
- `backend/app/metrics.py` - bias, MAE, RMSE, MAPE, nMAE, percentiles, breakdowns
- `backend/app/ingest.py` - pulls Elexon FUELHH (WIND) and WINDFOR into `data/elexon.db`
- `backend/app/sample_data.py` - synthetic data for UI work only
- `backend/app/main.py` - FastAPI: `/api/meta`, `/api/forecast`, `/api/metrics`, `/api/metrics/by-horizon`
- `backend/tests/` - pytest unit tests
- `frontend/` - React (Vite + Recharts)
- `Dockerfile`, `docker-compose.yml` - single image serving API + UI

## Run
```bash
# 1. Get data (once), then commit backend/data/elexon.db
cd backend && pip install -r requirements.txt && python -m app.ingest
python -m pytest
# 2a. Docker
cd .. && docker compose up --build        # http://localhost:8000
# 2b. Dev mode
cd backend && uvicorn app.main:app --reload
cd frontend && npm install && npm run dev  # http://localhost:5173
```

## Deploy to Heroku

The app is packaged as one Docker container: Heroku builds the React frontend and
serves it alongside the FastAPI API. The SQLite database is a committed, read-only
snapshot included in the image.

### Deploy with the Heroku CLI

Install the [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli), sign in,
and run these commands from the repository root:

```bash
heroku login
heroku create --stack container
git push heroku main
```

Heroku uses `heroku.yml` to build the root `Dockerfile`; the container starts with
the `CMD` defined there and listens on Heroku's `$PORT`.

### Deploy from GitHub

Create a Heroku app using the `container` stack, connect it to this repository in
the app's **Deploy** tab, and deploy the `main` branch. Enable automatic deploys
there if you want future pushes to `main` to publish automatically.
