# Bulk Certificate Generator

A backend REST API that accepts **bulk certificate generation requests** for a list of recipients, generates a **PDF** and **PNG** certificate per recipient from a single predefined template, tracks generation progress, and allows generated certificates to be retrieved.

Built with **Django**, **Django REST Framework**, and a relational database (**SQLite** by default, **MySQL**-ready).

---

## Table of contents

1. [Features](#features)
2. [Tech stack](#tech-stack)
3. [Project structure](#project-structure)
4. [Setup](#setup)
5. [Running the application](#running-the-application)
6. [Running the tests](#running-the-tests)
7. [Submitting a certificate generation request](#submitting-a-certificate-generation-request)
8. [Retrieving generated certificates](#retrieving-generated-certificates)
9. [API reference](#api-reference)
10. [Design decisions](#design-decisions)
11. [Validation & failure handling](#validation--failure-handling)
12. [Bulk processing](#bulk-processing)
13. [Testing](#testing)
14. [Known issues / limitations](#known-issues--limitations)
15. [Future improvements](#future-improvements)

---

## Features

- **Bulk submission** — one request, many recipients (up to 500 per job)
- **Per-recipient validation** with clear, indexed error messages
- **Background processing** via `concurrent.futures.ThreadPoolExecutor` (no Celery, no Redis)
- **Dual output** — every certificate generated as both **PDF** (`reportlab`) and **PNG** (`Pillow`)
- **Isolated failures** — one bad recipient never blocks the others
- **Progress tracking** — poll a job to see overall and per-certificate status
- **File retrieval** — direct `/media/...` URLs returned in the API response
- **Auto-generated API docs** — Swagger UI at `/api/docs/`
- **Django admin integration** — inspect jobs and certificates at `/admin/`

---

## Tech stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.10+ |
| Framework | Django 4.2+ |
| API | Django REST Framework |
| ORM | Django ORM |
| Database | SQLite (dev), MySQL 8 (prod, switchable via env) |
| PDF rendering | `reportlab` |
| PNG rendering | `Pillow` |
| Background work | `concurrent.futures.ThreadPoolExecutor` (stdlib) |
| API docs | `drf-spectacular` |
| Config | `python-dotenv` |
| Tests | `pytest` + `pytest-django` + DRF `APIClient` |

---

## Project structure

```
bulk-certificate-generator/
├── config/                         # Django project (settings, root URLs)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── certificates/                   # Domain app
│   ├── models.py                   # Job, Certificate
│   ├── serializers.py              # Request validation + response shapes
│   ├── views.py                    # API endpoints
│   ├── urls.py                     # API routes
│   ├── tasks.py                    # Background worker (ThreadPoolExecutor)
│   ├── renderers.py                # Dispatcher → pdf_renderer + png_renderer
│   ├── template_config.py          # Single source of truth for the design
│   ├── pdf_renderer.py             # reportlab PDF generation
│   ├── png_renderer.py             # Pillow PNG generation
│   ├── admin.py                    # Django admin registration
│   ├── migrations/
│   └── tests/                      # pytest test suite
│       ├── conftest.py
│       ├── test_creation.py
│       ├── test_validation.py
│       ├── test_generation.py
│       ├── test_status.py
│       ├── test_failure_handling.py
│       └── test_retrieval.py
│
├── media/                          # Generated PDFs / PNGs (gitignored)
│   └── certificates/<job_id>/
│
├── manage.py
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
└── README.md
```

---

## Setup

### Prerequisites

- **Python 3.10** or newer
- **pip** and **venv** (bundled with Python)
- *(Optional)* **MySQL 8** if you want to use MySQL instead of SQLite

### 1. Clone the repository

```bash
git clone <your-repo-url> bulk-certificate-generator
cd bulk-certificate-generator
```

### 2. Create and activate a virtual environment

**Linux / macOS:**

```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example env file:

**Linux / macOS:**

```bash
cp .env.example .env
```

**Windows (PowerShell):**

```powershell
Copy-Item .env.example .env
```

Generate a Django secret key and paste it into `.env` as `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Your `.env` should look like:

```env
SECRET_KEY=<paste-generated-key-here>
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost

DB_ENGINE=sqlite
DB_NAME=certificates_db
DB_USER=root
DB_PASSWORD=
DB_HOST=127.0.0.1
DB_PORT=3306
```

> **Note:** `DEBUG=True` is for local development only. Set it to `False` in production.

### 5. (Optional) Switch to MySQL

Edit `.env`:

```env
DB_ENGINE=mysql
DB_NAME=certificates_db
DB_USER=youruser
DB_PASSWORD=yourpassword
DB_HOST=127.0.0.1
DB_PORT=3306
```

Then run migrations (below). No code changes are required.

### 6. Apply database migrations

```bash
python manage.py migrate
```

This creates `db.sqlite3` (SQLite) or the corresponding MySQL tables.

### 7. (Optional) Create an admin user

For inspecting jobs and certificates in Django admin:

```bash
python manage.py createsuperuser
```

---

## Running the application

Start the development server:

```bash
python manage.py runserver
```

The API is available at **`http://127.0.0.1:8000/`**.

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:8000/api/jobs/` | API root for jobs |
| `http://127.0.0.1:8000/api/docs/` | Interactive Swagger UI |
| `http://127.0.0.1:8000/api/schema/` | OpenAPI schema (YAML) |
| `http://127.0.0.1:8000/admin/` | Django admin (if superuser created) |

---

## Running the tests

Run the full test suite:

```bash
pytest
```

Expected output:

```
...............                                                          [100%]
15 passed in ~1.5s
```

The suite covers the six scenarios required by the specification:

1. **Creating a generation job** — `test_creation.py`
2. **Input validation** — `test_validation.py`
3. **Certificate generation** — `test_generation.py`
4. **Job status / progress** — `test_status.py`
5. **Handling an individual certificate failure** — `test_failure_handling.py`
6. **Retrieving generated certificates** — `test_retrieval.py`

---

## Submitting a certificate generation request

### Endpoint

```
POST /api/jobs/
```

**Headers:**

```
Content-Type: application/json
```

**Body:**

```json
{
  "course_name": "Advanced Django",
  "issued_on": "2025-06-01",
  "recipients": [
    { "name": "Alice Smith", "email": "alice@example.com" },
    { "name": "Bob Jones",   "email": "bob@example.com" },
    { "name": "Carol White" }
  ]
}
```

### Example — using `curl`

Save the body to a file (recommended on Windows to avoid shell quoting issues):

**`payload.json`:**

```json
{
  "course_name": "Advanced Django",
  "issued_on": "2025-06-01",
  "recipients": [
    { "name": "Alice Smith", "email": "alice@example.com" },
    { "name": "Bob Jones",   "email": "bob@example.com" }
  ]
}
```

**Submit:**

```bash
curl -X POST http://127.0.0.1:8000/api/jobs/ \
     -H "Content-Type: application/json" \
     --data-binary "@payload.json"
```

**Windows PowerShell:**

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/jobs/ -H "Content-Type: application/json" --data-binary "@payload.json"
```

### Response (`201 Created`)

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "total": 2,
  "succeeded": 0,
  "failed": 0,
  "created_at": "2025-06-01T12:00:00Z",
  "started_at": null,
  "finished_at": null,
  "certificates": [
    {
      "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      "recipient_name": "Alice Smith",
      "recipient_email": "alice@example.com",
      "course_name": "Advanced Django",
      "issued_on": "2025-06-01",
      "status": "pending",
      "pdf_url": null,
      "png_url": null,
      "error_message": null,
      "created_at": "2025-06-01T12:00:00Z",
      "updated_at": "2025-06-01T12:00:00Z"
    },
    { "id": "...", "recipient_name": "Bob Jones", "status": "pending", ... }
  ]
}
```

The job is processed in the background. The response reflects the state at the moment the job was created. **Poll the job to see progress.**

### Checking progress

```
GET /api/jobs/{id}/
```

**Response (after processing):**

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "total": 2,
  "succeeded": 2,
  "failed": 0,
  "started_at": "2025-06-01T12:00:00.123Z",
  "finished_at": "2025-06-01T12:00:01.456Z",
  "certificates": [
    {
      "id": "aaaaaaaa-...",
      "recipient_name": "Alice Smith",
      "status": "success",
      "pdf_url": "http://127.0.0.1:8000/media/certificates/550e.../aaaaaaaa-....pdf",
      "png_url": "http://127.0.0.1:8000/media/certificates/550e.../aaaaaaaa-....png",
      "error_message": null
    },
    { "recipient_name": "Bob Jones", "status": "success", "pdf_url": "...", "png_url": "..." }
  ]
}
```

### Job status values

| Status | Meaning |
|--------|---------|
| `pending` | Created; worker hasn't started |
| `processing` | Worker is generating certificates |
| `completed` | All recipients succeeded |
| `partial` | Some succeeded, some failed |
| `failed` | All recipients failed |

### Certificate status values

| Status | Meaning |
|--------|---------|
| `pending` | Not yet processed |
| `success` | Files ready; `pdf_url` and `png_url` populated |
| `failed` | Generation failed; `error_message` populated |

---

## Retrieving generated certificates

Each certificate's `pdf_url` and `png_url` in the status response are **direct download links** to the generated files.

### Example

From the status response:

```json
"pdf_url": "http://127.0.0.1:8000/media/certificates/550e.../aaaaaaaa-....pdf",
"png_url": "http://127.0.0.1:8000/media/certificates/550e.../aaaaaaaa-....png"
```

Open either URL in a browser, or:

```bash
curl -O http://127.0.0.1:8000/media/certificates/550e.../aaaaaaaa-....pdf
```

**The files are always available once the certificate's status is `success`.**

### Optional — download endpoint with forced download

```
GET /api/jobs/{job_id}/certificates/{cert_id}/download/?format=pdf
GET /api/jobs/{job_id}/certificates/{cert_id}/download/?format=png
```

Returns the file with `Content-Disposition: attachment; filename="..."`.

> **Note:** This endpoint is registered and documented in Swagger, but on some Windows dev setups it returns a 404 due to a URL-resolver caching quirk. Use the `/media/...` URLs returned in the API response — they always work.

---

## API reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/jobs/` | Create a bulk certificate generation job |
| `GET` | `/api/jobs/` | List all jobs |
| `GET` | `/api/jobs/{id}/` | Get job status with nested certificates |
| `GET` | `/api/jobs/{job_id}/certificates/{cert_id}/download/?format=pdf\|png` | Download a certificate file |
| `GET` | `/api/schema/` | OpenAPI schema |
| `GET` | `/api/docs/` | Swagger UI |

### Validation errors

When the request body is invalid, the API returns `400 Bad Request` with **per-index errors**:

```json
{
  "recipients": {
    "1": { "email": ["Enter a valid email address."] }
  }
}
```

Only failing recipients are listed; valid ones are omitted. The index corresponds to the position in the `recipients` array (0-based).

Missing or invalid top-level fields are reported by field name:

```json
{
  "course_name": ["This field is required."],
  "issued_on": ["Date has wrong format. Use YYYY-MM-DD."],
  "recipients": ["This list may not be empty."]
}
```

---

## Design decisions

### Certificate template — shared single source of truth

The certificate design (title, fonts, colors, positions, borders, static text) lives in **one file**: `certificates/template_config.py`. Both the PDF renderer and the PNG renderer **read from this shared config**. This ensures the two output formats stay visually consistent and any design change is made in exactly one place.

### PDF + PNG — "draw twice" approach

Both formats are generated by **drawing the same design twice**:

- `pdf_renderer.py` uses `reportlab` — a vector PDF, printable and crisp at any zoom
- `png_renderer.py` uses `Pillow` — a raster image, easy to preview and share

**Alternatives considered and rejected:**

| Alternative | Why rejected |
|-------------|--------------|
| Generate PDF, then convert to PNG with Poppler / `pdf2image` | Requires a system binary (Poppler). Our goal was zero system dependencies. |
| Rasterize once with Pillow, then embed the PNG in a PDF | PDF text becomes an image — larger files, no text selection, poor print quality. |
| Hardcode the design separately in each renderer | Two sources of truth — guaranteed to drift over time. |

The "draw twice" approach keeps both renderers **stateless**, **testable in isolation**, and visually identical.

### Cross-platform fonts

- **PDF:** uses reportlab's built-in Helvetica family. No font files required — works everywhere.
- **PNG:** tries a list of common TrueType fonts (`Arial` on Windows, `DejaVuSans` on Linux, `Arial` on macOS). Falls back to Pillow's default bitmap font if none is found.

### UUID primary keys

Both `Job` and `Certificate` use UUID primary keys:

- **Non-guessable** — safe to expose in URLs without enumeration
- **Collision-free file names** — `media/certificates/<job_id>/<cert_id>.pdf`
- **Distributed-friendly** — no central sequence required

### Denormalized counters on `Job`

`Job.total`, `Job.succeeded`, and `Job.failed` duplicate information derivable from `Certificate` rows. They exist because the status endpoint is polled frequently by clients — returning counts from a single `SELECT` avoids a `COUNT(*)` on every request. Final counts are **recomputed** at the end of processing, so they can never drift.

---

## Validation & failure handling

### Two layers of validation

| Layer | When | Outcome |
|-------|------|---------|
| **Input validation** (DRF serializers) | Before the job is created | Reject the entire request with per-index errors. No job row is created. |
| **Generation failures** (background worker) | After the job is created | The job proceeds; failed certificates are marked `failed` with an `error_message`. |

This split matches the spec: invalid input is a client problem (fix and resubmit); a runtime rendering failure is a per-certificate concern.

### Per-certificate failure isolation

The worker wraps each certificate's generation in its own `try/except`:

```python
for cert in certificates:
    try:
        render_certificate(cert)          # may raise
        cert.status = "success"
    except Exception as exc:
        cert.status = "failed"
        cert.error_message = f"{type(exc).__name__}: {exc}"
    cert.save()
```

**One failing certificate never prevents the others from being generated.** The job's final status reflects this:

- All succeeded → `completed`
- All failed → `failed`
- Mixed → `partial`

This behaviour is locked in by `test_failure_handling.py::test_one_failure_does_not_block_siblings`.

---

## Bulk processing

### Choice: `concurrent.futures.ThreadPoolExecutor`

The worker uses a **module-level `ThreadPoolExecutor`** (Python standard library) with a bounded pool size (4 workers). When a job is submitted, `enqueue_job(job_id)` submits it to the pool and returns immediately; the HTTP response goes back to the client before processing starts.

### Why threads, not Celery

| Aspect | `ThreadPoolExecutor` (ours) | Celery + Redis |
|--------|-----------------------------|----------------|
| Extra infrastructure | None — pure stdlib | Redis (or RabbitMQ) + Celery worker process |
| Setup complexity | 5 lines of code | Config files, broker, worker process to supervise |
| Survives process crash | ❌ In-flight jobs lost | ✅ Tasks persisted in broker |
| Distributed across machines | ❌ | ✅ |
| Fit for this task | ✅ Single-server assignment | Overkill |

**Tradeoffs (documented honestly):**

- **In-process only.** If the Django process dies mid-job, in-flight work is lost. Celery would persist it in a broker.
- **Not distributed.** Cannot scale across machines without a broker.
- **SQLite caveat.** SQLite is not designed for concurrent writers. We set `OPTIONS.timeout = 20` and keep `max_workers=4` to avoid lock contention. **MySQL is recommended in production.**
- **Swap path.** The interface is designed so replacing the pool with Celery later is a small change: `views.py` calls `enqueue_job(job.id)`; replacing that one line with `process_job.delay(job.id)` is enough.

### DB connection handling in worker threads

Django opens one DB connection per thread. Worker threads are not request threads, so Django does not auto-close their connections. `_process_job` calls `connection.close()` in a `finally:` block to prevent connection leaks — a standard pattern for Django background work without Celery.

---

## Testing

### Coverage

The test suite (`certificates/tests/`) covers:

| File | Scenario |
|------|----------|
| `test_creation.py` | Creating a job; worker enqueue regression test; empty recipients rejected |
| `test_validation.py` | Per-index errors; blank names; missing fields; invalid date; recipient cap |
| `test_generation.py` | Worker produces real PDF + PNG files with correct signatures |
| `test_status.py` | Job detail returns nested certificates with URLs; unknown job → 404 |
| `test_failure_handling.py` | **One failure doesn't block siblings**; all failures → job `failed` |
| `test_retrieval.py` | Files exist on disk with correct magic bytes; API returns URLs |

### Test isolation

- Every test uses a **temp `MEDIA_ROOT`** (`tmp_path` fixture, autouse), so test runs never pollute the real `media/` folder.
- Worker-touching tests use `pytest.mark.django_db(transaction=True)` to let background threads see committed rows (SQLite requires this).
- Synchronous worker tests call `_process_job(job_id)` directly — deterministic, fast.

### Running

```bash
pytest                 # all tests
pytest -v              # verbose
pytest certificates/tests/test_failure_handling.py   # one file
```

---

## Known issues / limitations

- **`/download/` endpoint 404 on some local setups.** The route is registered and documented in Swagger, and `reverse()` + `resolve()` both work correctly from a fresh Python process. On certain Windows dev environments the running server intermittently returns 404. **Workaround:** use the `pdf_url` / `png_url` fields returned by the status endpoint — files are always available at those URLs.
- **Latin-1 character set for text.** reportlab's built-in Helvetica family handles Latin-1; complex scripts (Cyrillic, CJK, emoji) will raise `UnicodeEncodeError`, and the certificate will be marked `failed` with a clear `error_message`. Adding a TTF font file would fix this but was not required for the assignment.
- **No authentication.** All endpoints are public. Production would add DRF authentication and per-user job isolation.
- **No pagination on `GET /api/jobs/`.** For a large number of jobs, add `LimitOffsetPagination`.
- **Single-server.** The thread pool is per-process; horizontal scaling requires Celery or a task queue.

---

## Future improvements

- **Celery + Redis** for durable, distributed job processing
- **ZIP download** for a whole job (all PDFs / PNGs in one archive)
- **Email delivery** of certificates on job completion
- **Multiple templates** selectable per job (event certificates, course certificates, awards)
- **Signed URLs (S3)** with expiration for direct, secure downloads
- **Web UI** (`/ui/`) with a submit form and click-to-download buttons
- **Progress streaming** via Server-Sent Events (SSE) instead of polling
- **Authentication + per-user jobs**

---

## License

MIT — or your preferred license.