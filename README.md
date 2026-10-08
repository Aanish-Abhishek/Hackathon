# TraceFix AI

TraceFix is a desktop incident-analysis frontend backed by a FastAPI service. The API
accepts UTF-8 `.log`/`.txt` uploads, inspects the Python examples in
`backend/dummy_repo/`, and asks an OpenAI GPT model for evidence-based findings.
The previous JSON knowledge-base rules are no longer used by the frontend.

## Requirements

- Python 3.10 or newer
- An OpenAI API key for GPT analysis

## Start the backend

From the project root, create and activate a virtual environment, then install
dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:OPENAI_API_KEY = "your-api-key"
# Optional: $env:OPENAI_MODEL = "gpt-4o-mini"
uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```

The service health check is `http://127.0.0.1:8000/health`; interactive API
documentation is at `http://127.0.0.1:8000/docs`.

## Start the UI

In a second terminal, from the project root, run:

```powershell
python main.py
```

The frontend posts the current log text to `POST /analyze-logs` as multipart field
`files` and renders the response's `findings` in the existing Overview, Evidence,
and Actions tabs. Set `TRACEFIX_BACKEND_URL` if the API is hosted elsewhere.
The API accepts up to 10 `.log`/`.txt` files, each up to 1 MB, with a 2 MB total
upload limit. UTF-8 text is required.

To exercise the upload endpoint without the UI, run this from the project root:

```powershell
curl.exe -F "files=@backend/dummy_repo/logs/sample_error.log" `
  http://127.0.0.1:8000/analyze-logs
```

Each finding includes `error_type`, `suspected_root_cause`, `file`, `function`,
`suggested_fix`, `severity`, `confidence`, and supporting `evidence`.

For browser-based frontends, configure `BACKEND_CORS_ORIGINS` as a
comma-separated allowlist of trusted origins before starting the backend.

## Sample repository and test

`backend/dummy_repo/` contains intentionally buggy trading application modules
covering order validation, risk, portfolio valuation, pricing, execution,
settlement, positions, market data, reconciliation, and account access. The
`logs/` directory contains sample stack traces for several of those defects;
upload any `.log` file through the UI or API.

Run backend tests from the backend directory:

```powershell
cd backend
python -m unittest discover -s tests
```

The API returns 422 for invalid log uploads, 503 if `OPENAI_API_KEY` is missing,
502 for provider failures, and 500 if the expected repository files are missing.
Uploaded logs and repository source are sent to the configured OpenAI model;
sanitize sensitive data before analysis.
