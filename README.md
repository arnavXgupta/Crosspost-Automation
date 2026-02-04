# Social Media Pipeline (MVP)

API-only MVP that turns an Instagram reel script into a **Twitter/X thread** (via Composio).

It stores jobs and platform post status in a simple SQLite DB.

## Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env`:
- `GEMINI_API_KEY` / `GEMINI_MODEL` (for content generation)
- `COMPOSIO_API_KEY` (for Twitter/X publishing)
- `COMPOSIO_USER_ID` (Composio user ID that has the connected Twitter account; defaults to "default")

## Run

```bash
uvicorn app.main:app --reload
```

Health:
- `GET /api/v1/health`

## API usage

### 1) Create a job (and auto-generate preview)

```bash
curl -X POST http://127.0.0.1:8000/api/v1/scripts?sync=true ^
  -H "Content-Type: application/json" ^
  -d "{\"title\":\"Test\",\"content\":\"Here is my reel script...\",\"metadata\":{\"topic\":\"AI\"}}"
```

Response:

```json
{ "job_id": "...", "status": "pending" }
```

### 2) Fetch job status + generated content

```bash
curl http://127.0.0.1:8000/api/v1/jobs/<job_id>
```

### 3) Generate preview explicitly

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs/<job_id>/preview?sync=true
```

### 4) Publish/schedule

```bash
curl -X POST http://127.0.0.1:8000/api/v1/jobs/<job_id>/publish?sync=true ^
  -H "Content-Type: application/json" ^
  -H "Idempotency-Key: demo-123" ^
  -d "{\"publish\":true,\"generate_if_missing\":true,\"regenerate\":false}"
```

## Tests (no extra deps)

```bash
python -m unittest discover -s tests -p "test_*.py"
```

## Notes

- For MVP reliability, jobs run via FastAPI `BackgroundTasks` (non-durable). Use `?sync=true` while developing.
- SQLite tables are auto-created on startup. Upgrade path is Postgres + migrations.
