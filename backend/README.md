# Lyftr AI backend

## 1. Create API keys
Open https://aistudio.google.com/app/apikey, create two Gemini API keys, and copy them.
For independent quota pools, use keys from separate Google Cloud projects where possible.

## 2. Configure
From the `backend` directory:
- Create a virtual environment: `python -m venv .venv`
- Activate it (Windows PowerShell): `.venv\\Scripts\\Activate.ps1`
- Install: `pip install -r requirements.txt`
- Copy `.env.example` to `.env` and add your two keys.

## 3. Run
`uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`

Swagger UI: http://127.0.0.1:8000/docs

## 4. Required endpoints
- `GET /health`
- `POST /chat`
- `GET /sessions/{session_id}/messages`

## 5. Test failover
In Swagger, use POST /chat and add header:
`X-Simulate-Failure: key_1=429`
Expected: HTTP 200 and `metadata.key_id` is `key_2`.

Use `X-Simulate-Failure: *=429` to expect HTTP 503.

## Notes
The app keeps a deterministic exact-request response cache in process memory and also enables LiteLLM's built-in local cache. Both are single-process caches; use one backend worker for this assignment. SQLite history is stored in `app.db` for local development.
