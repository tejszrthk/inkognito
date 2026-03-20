# Inkognito Pipeline

Unified background verification pipeline for Indian matrimonial profile checks.

## What it does

The pipeline runs 13 modules and generates a JSON report with prioritized findings.

- Always-on: `eCourts`, `MCA21`, `GST`, `Google Search`, `Property Records`, `Social Media`, `Reverse Image Search`, `Phone Intelligence`, `Matrimonial Cross-check`
- Conditional:
  - `NCDRC`, `NCLT` when business data is present
  - `SEBI` when finance role is detected
  - `EPFO` when employer data is present

## Project files

- `inkognito_models.py`: shared dataclasses and report model
- `inkognito_pipeline.py`: module implementations and orchestration
- `test_runner.py`: setup checks + predefined test scenarios
- `test_cases.json`: external test subject fixtures used by `test_runner.py`
- `requirements.txt`: Python dependencies
- `.env.template` / `env.template`: environment variable templates

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.template .env
```

Fill required keys in `.env`:

- `LEGALKART_API_KEY`
- `SERP_API_KEY`
- `MCA_API_KEY`

`MCA_API_PROVIDER` defaults to `surepass`.

## Run Connected Web App

The frontend is now connected to the real backend pipeline (not a simulation).

```bash
# Start API + static frontend server
python api_server.py --host 127.0.0.1 --port 8000
```

Open:

`http://127.0.0.1:8000`

How it works:

- Frontend submits subject data to `POST /api/run`
- Frontend polls `GET /api/jobs/<job_id>` for live module status
- Completed runs persist JSON reports under `reports/`

## Vercel Deployment (Frontend)

If you deploy the UI on Vercel, you still need a separate Python backend for the pipeline.

Why: this pipeline is long-running and writes reports, so it is not a good fit for short-lived stateless serverless invocations.

Recommended architecture:

1. Deploy frontend on Vercel.
2. Deploy backend (`api_server.py`) on an always-on Python host (Render, Railway, Fly.io, VM, etc.) with HTTPS enabled.
3. Set the backend URL in `frontend/deploy-config.js`:

```js
window.INKOGNITO_API_BASE = 'https://your-backend-domain.example.com';
```

4. Redeploy frontend.

Quick override (no code edit):

- Open your deployed frontend with `?api_base=https://your-backend-domain.example.com`
- The app stores this URL in browser local storage for future runs.

Backend start command on a host:

```bash
python api_server.py --host 0.0.0.0 --port $PORT
```

## Testing

Use the following sequence for a clean verification pass.

```bash
# 1) Validate imports + env keys (no external calls)
python test_runner.py --dry

# 2) See all modules, triggers, and key dependencies
python test_runner.py --modules

# 3) Run a single scenario first
python test_runner.py --case 1

# 4) Run all scenarios
python test_runner.py
```

Test scenarios are loaded from `test_cases.json` (not hardcoded in Python).
You can provide a custom file with:

```bash
python test_runner.py --cases-file /path/to/your_cases.json
```

### Test cases

- `--case 1`: minimum profile (baseline always-on flow)
- `--case 2`: business-owner profile (triggers NCDRC, NCLT, SEBI, EPFO)
- `--case 3`: UP-focused property profile (property + phone + social focus)
- `--case 4`: maximum profile (all optional fields present)

### Output verification checklist

Each run writes JSON output under `reports/`.

- Confirm `modules_run` includes expected modules for the test case.
- Confirm skipped modules have `skipped: true` and a meaningful `skip_reason`.
- Confirm any failed module has an actionable `error` message.
- Review `total_findings`, `high_priority`, and `overall_flag` for reasonableness.

## Optional keys for deeper coverage

- `IMGBB_API_KEY`: required for reverse image upload workflow.
- `CAPTCHA_BYPASS_ENABLED`: defaults to `False`; legally flagged control for IGRS UP CAPTCHA automation.
- `CAPTCHA_API_KEY`: used only when `CAPTCHA_BYPASS_ENABLED=True` for internal testing.
- `SERP_API_KEY`: improves profile URL discovery and search coverage.

## Runtime timeout tuning

If your environment has slow/blocked network access, you can cap long modules:

- `NCLT_MAX_DURATION_SEC` (default: `25`)
- `PROPERTY_MAX_DURATION_SEC` (default: `75`)
- `LEGALKART_AUTH_TIMEOUT_SEC` (default: `4`)
- `LEGALKART_AUTH_RETRIES` (default: `1`)

## Running the pipeline directly

You can also run the demo subject in `inkognito_pipeline.py`:

```bash
python inkognito_pipeline.py
```

## Report structure

The current report model is based on `UnifiedReport`:

- `report_id`
- `subject_name`
- `generated_at`
- `overall_flag`
- `total_findings`
- `high_priority`
- `medium_priority`
- `modules_run` (per-module result and findings)

Use `report.to_dict()` for serialization.
# inkognito
# inkognito
