# Isometric Drawing to Automated MTO Generator

An industry-grade, full-stack piping engineering web application that automatically extracts a structured **Material Take-Off (MTO)** from piping isometric drawings (images or PDFs).

---

## 1. Project Overview & Architecture

This application automates the tedious, error-prone manual process of compiling piping bills of materials (BOM) from isometric drawings. By combining modern web technologies (Next.js and FastAPI) with state-of-the-art vision language models (NVIDIA Llama NIMs, Google Gemini API, and OpenRouter), the application processes uploaded drawings and parses them into standardized, structured piping components.

### High-Level Architecture Diagram

```text
                  +----------------------------------------------+
                  |              Next.js Frontend                |
                  |  - Drag-and-Drop File Upload (PNG/JPG/PDF)   |
                  |  - Side-by-Side Drawing & MTO Table Preview  |
                  |  - Interactive Summary Cards & CSV Export    |
                  +----------------------+-----------------------+
                                         |
                            POST /api/upload  →  202 Accepted
                            GET  /api/mto/{id}  (polling)
                            GET  /api/mto/{id}/csv
                                         |
                                         v
                  +----------------------------------------------+
                  |               FastAPI Backend                |
                  |                                              |
                  |  ┌─────────────────────────────────────┐    |
                  |  │  Rate Limiter (slowapi)              │    |
                  |  │  5 uploads/min · 60 req/min default  │    |
                  |  └────────────────┬────────────────────┘    |
                  |                   │                          |
                  |  ┌────────────────▼────────────────────┐    |
                  |  │  /api/upload  →  202 PENDING         │    |
                  |  │  BackgroundTask spawned immediately   │    |
                  |  └────────────────┬────────────────────┘    |
                  +-------------------│--------------------------+
                                      │ (async background task)
                                      v
                  +----------------------------------------------+
                  |         1. Preprocessing Service             |
                  |    asyncio.to_thread → thread pool           |
                  |  - PDF rendering (PyMuPDF @ 150 DPI)         |
                  |  - Resolution normalisation (max 2048px)     |
                  |  - Base64 JPEG Data URL generation           |
                  +----------------------+-----------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |       2. Vision AI Extraction Pipeline       |
                  |  Priority: NVIDIA → Gemini → OpenRouter →    |
                  |            MockExtractor (fallback)          |
                  |    asyncio.to_thread → thread pool           |
                  |  - 3× retry with exponential backoff         |
                  +----------------------+-----------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |         3. Validation & Derivation           |
                  |  - Schema checks (Pydantic v2 MTO models)    |
                  |  - NPS Normalisation  (6 → 6")               |
                  |  - Derives GASKET & BOLT counts from joints  |
                  |  - Computes totals & flags discrepancies     |
                  +----------------------+-----------------------+
                                         |
                                         v
                  +----------------------------------------------+
                  |       4. SQLite Job Store (aiosqlite)        |
                  |  - Persistent across restarts / hot-reloads  |
                  |  - Jobs indexed by status for fast lookup    |
                  |  - File: backend/jobs.db (git-ignored)       |
                  +----------------------------------------------+
```

### Architecture Decisions

* **Next.js App Router**: Used over the Pages Router because it provides clean server-component boundaries, robust layouts, and straightforward API integration.
* **Async Fire-and-Respond upload pattern**: `POST /api/upload` returns `202 Accepted` with a `job_id` and `status: PENDING` immediately. Extraction runs as a `BackgroundTask`. The frontend polls `GET /api/mto/{job_id}` until status is `COMPLETED` or `FAILED`.
  * *Why*: Eliminates HTTP gateway timeouts (default 30–60 s) caused by LLM calls that can take up to 90 s. Keeps the API responsive under load.
* **Thread pool offloading**: Both CPU-bound preprocessing (PIL/PyMuPDF) and blocking LLM HTTP calls are wrapped in `asyncio.to_thread()`, keeping the event loop free for concurrent requests.
* **Modular Monolith**: A single deployable service with clean internal boundaries (routes / services / schemas / store). Avoids the operational overhead of microservices while still permitting easy extraction of individual services later.
* **SQLite persistence**: Jobs survive server restarts and hot-reloads. `aiosqlite` keeps everything async without a separate database server.
* **Rate limiting via `slowapi`**: Prevents a single client from exhausting the LLM API budget (5 uploads/minute per IP).

---

## 2. Screenshots

A visual walkthrough of the three core screens in the application:

### 🏠 Landing — Upload Isometric Drawing
> Drag & drop or browse for a PNG, JPG, or PDF blueprint sheet (up to 20 MB). Key feature cards are shown below the upload zone.

![Landing page showing the drag-and-drop upload interface](assets/screenshots/landing.jpeg)

---

### ⚙️ Processing — Vision AI Pipeline in Progress
> Once a file is submitted, the app shows a real-time status tracker as it runs through Vision LLM extraction, ASME validation, and joint consumables calculation.

![Processing screen with live pipeline status indicators](assets/screenshots/processing.jpeg)

---

### 📊 Results — Workspace Dashboard & MTO Table
> After extraction completes, the full Material Take-Off is displayed — drawing title block metadata, summary cards (pipe length, fittings, flanges, valves, gaskets, bolt sets), and a searchable, filterable MTO table with CSV export.

![Results dashboard with drawing metadata and full MTO table](assets/screenshots/result.jpeg)

---

## 3. Project Structure

```
project/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, lifespan, CORS, logging, health
│   │   ├── limiter.py               # Shared slowapi rate-limiter instance
│   │   ├── config.py                # Pydantic-settings (reads .env)
│   │   ├── schemas.py               # Pydantic models: MTOItem, MTOResponse, …
│   │   ├── store.py                 # Async SQLite job store (aiosqlite)
│   │   ├── routes/
│   │   │   └── mto.py               # /api/upload, /api/mto/{id}, /api/mto/{id}/csv
│   │   └── services/
│   │       ├── extractor.py         # VisionExtractor ABC + factory
│   │       ├── preprocessor.py      # PDF/image → base64 JPEG
│   │       ├── validator.py         # Normalization + GASKET/BOLT derivation
│   │       ├── nvidia_extractor.py  # NVIDIA NIM (Llama 3.2 Vision)
│   │       ├── gemini_extractor.py  # Google Gemini API
│   │       ├── openrouter_extractor.py # OpenRouter (any vision model)
│   │       └── mock_extractor.py    # Static fallback (no key required)
│   ├── tests/
│   ├── sample_drawings/
│   ├── requirements.txt
│   ├── .env.example
│   ├── .gitignore
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                     # Next.js App Router pages
│   │   └── components/              # UploadZone, MtoTable, MtoSummaryCards, DrawingMeta
│   ├── package.json
│   └── Dockerfile
└── docker-compose.yml
```

---

## 4. Setup & Running Locally

### Version Requirements

| Runtime | Minimum Version |
| :--- | :--- |
| Python | 3.11+ |
| Node.js | 18.x+ |

### Backend Setup (FastAPI)

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   # .venv\Scripts\activate         # Windows PowerShell
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   # Open .env and fill in at least one API key.
   # If all keys are blank, the app falls back to the mock pipeline automatically.
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   On first start, `jobs.db` is created automatically in `backend/`.

6. **Interactive API docs**: Visit [http://localhost:8000/docs](http://localhost:8000/docs) to explore and test all endpoints via Swagger UI.

### Frontend Setup (Next.js)

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Configure the API URL (optional — defaults to localhost):
   ```env
   # frontend/.env.local
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Start the development server:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

### Docker Compose (Full Stack)

To run both services together with a single command:
```bash
docker-compose up --build
```
Frontend: [http://localhost:3000](http://localhost:3000) · Backend: [http://localhost:8000](http://localhost:8000)

---

## 5. Environment Variables

All variables live in `backend/.env` (copy from `.env.example`, never commit the real file).

| Variable | Default | Description |
| :--- | :--- | :--- |
| `NVIDIA_API_KEY` | — | NGC API key from [build.nvidia.com](https://build.nvidia.com). First priority provider. |
| `NVIDIA_MODEL` | `meta/llama-3.2-90b-vision-instruct` | NVIDIA vision model identifier. |
| `NVIDIA_BASE_URL` | `https://integrate.api.nvidia.com/v1/chat/completions` | NGC completion endpoint. |
| `GEMINI_API_KEY` | — | Google AI Studio key from [aistudio.google.com](https://aistudio.google.com). Second priority. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Google Gemini vision model. |
| `OPENROUTER_API_KEY` | — | [OpenRouter](https://openrouter.ai) key. Third priority. |
| `OPENROUTER_MODEL` | `nvidia/nemotron-nano-12b-v2-vl:free` | OpenRouter vision model. |
| `HOST` | `0.0.0.0` | Backend bind address. |
| `PORT` | `8000` | Backend port. |
| `FRONTEND_URL` | `http://localhost:3000` | Allowed CORS origin. |
| `MAX_FILE_SIZE_MB` | `20` | Maximum accepted upload size. |

**Provider priority**: `NVIDIA_API_KEY` → `GEMINI_API_KEY` → `OPENROUTER_API_KEY` → Mock (no key required).

---

## 6. How the AI Pipeline Works

### Step 1 — Preprocessing (`app/services/preprocessor.py`)

Runs in a thread pool via `asyncio.to_thread` to avoid blocking the async event loop.

* **Magic-byte detection**: Identifies PDF vs. image by inspecting raw bytes (`%PDF` prefix), not the filename.
* **PDF rendering**: First page rendered to PNG at 150 DPI using PyMuPDF (fitz).
* **Resolution cap**: Any dimension > 2048px is downscaled (aspect-ratio preserved) with Lanczos resampling to keep token count and API latency optimal.
* **Format normalisation**: Converts to RGB JPEG at 85% quality; outputs a `data:image/jpeg;base64,…` Data URL.

### Step 2 — Extraction (`app/services/extractor.py` + provider modules)

Runs in a thread pool via `asyncio.to_thread` — LLM HTTP calls are synchronous/blocking and must not touch the event loop.

The factory `get_extractor(settings)` selects the active provider at runtime:

```
NVIDIA_API_KEY set?     → NvidiaExtractor   (Llama 3.2 Vision NIM)
GEMINI_API_KEY set?     → GeminiExtractor   (Gemini 2.5 Flash)
OPENROUTER_API_KEY set? → OpenRouterExtractor (configurable model)
(none)                  → MockExtractor     (static reference output)
```

**Prompt strategy** (identical across all providers):
* Role instruction: "piping engineering AI assistant"
* Engineering context: ASME B16.9 / B16.5 / B16.34 / B36.10 vocabulary
* Category constraints: `PIPE | FITTING | FLANGE | VALVE | SUPPORT | WELD` only
* Explicit exclusion of `GASKET` and `BOLT` (derived programmatically in Step 3 — prevents LLM counting errors and wasteful output tokens)
* Strict JSON schema in the prompt with field-level examples
* Low temperature (0.2) for deterministic, repeatable output
* All providers use `response_format: json_object` where supported

**Reliability**: 3× retry with exponential backoff (1 s, 2 s). `ExtractionError` is not retried — it signals a terminal failure. If the primary extractor fails, the route handler falls back to `MockExtractor`.

### Step 3 — Validation & Derivation (`app/services/validator.py`)

* **Schema validation**: Raw LLM JSON is parsed into Pydantic v2 `MTOItem` / `DrawingMetadata` models with custom field and model validators.
* **NPS normalisation**: Sizes like `6` or `6x4` are fixed to standard ANSI format (`6"`, `6"x4"`).
* **Unit enforcement**: Units are always overridden by category — the LLM is never trusted for this:
  * `PIPE` → `M` (metres)
  * `BOLT` → `SET`
  * Everything else → `EA`
* **Consumable derivation**:

  ```
  Total flanged joints = Flange qty + Flanged-valve qty

  Gaskets needed  = joints − existing_gasket_qty   (if > 0)
  Bolt sets needed = joints − existing_bolt_qty    (if > 0)
  ```

  Derived items inherit size and rating from the first extracted flange.
* **Summary reconciliation**: Pipe length, fitting/flange/valve/gasket/bolt counts are recomputed from validated items. If the LLM's own summary deviates > 5% from computed totals, a QA warning remark is appended to pipe rows.
* **Sequential re-numbering**: `item_no` is always assigned sequentially after derivation — LLM numbering is discarded.

### Step 4 — Async Job Store (`app/store.py`)

Backed by `aiosqlite` (async SQLite). Schema:

```sql
CREATE TABLE jobs (
    job_id    TEXT PRIMARY KEY,
    status    TEXT NOT NULL,        -- PENDING | RUNNING | COMPLETED | FAILED
    data      TEXT NOT NULL,        -- Full MTOResponse serialized as JSON
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_jobs_status ON jobs(status);
```

The DB file (`backend/jobs.db`) is created automatically on first startup via the FastAPI lifespan hook and is excluded from version control via `.gitignore`.

---

## 7. API Reference

### Request / Response Flow

```
POST /api/upload
  → 202 Accepted
  { "job_id": "uuid", "status": "PENDING" }   ← returned instantly

  [background] PENDING → RUNNING → COMPLETED/FAILED

GET /api/mto/{job_id}             ← poll until COMPLETED or FAILED
  → 200 { job_id, status, drawing_meta, items[], summary, image_b64, ... }

GET /api/mto/{job_id}/csv         ← only available when COMPLETED
  → 200  text/csv  (attachment)
```

### Endpoint Table

| Method | Endpoint | Rate Limit | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | 60/min | Liveness check — returns `status`, `provider`, `version`, `uptime_s`, `jobs_total`. |
| `POST` | `/api/upload` | **5/min** | Upload PNG, JPEG, or PDF. Returns `{ job_id, status: PENDING }` immediately (`202`). |
| `GET` | `/api/mto/{job_id}` | 60/min | Poll for job status and full MTO payload. Status: `PENDING → RUNNING → COMPLETED / FAILED`. |
| `GET` | `/api/mto/{job_id}/csv` | 60/min | Stream MTO as UTF-8 CSV. Returns `409 Conflict` if job is not yet `COMPLETED`. |

### Error Responses

| Status | Trigger |
| :--- | :--- |
| `400` | Empty file body |
| `409` | CSV requested before job is `COMPLETED` |
| `413` | File exceeds `MAX_FILE_SIZE_MB` |
| `415` | Unsupported MIME type (only `image/png`, `image/jpeg`, `application/pdf` accepted) |
| `429` | Rate limit exceeded |
| `404` | `job_id` not found |

---

## 8. Rate Limiting

Implemented via [`slowapi`](https://github.com/laurentS/slowapi) (starlette-compatible `limits` wrapper):

| Scope | Limit |
| :--- | :--- |
| `POST /api/upload` | **5 requests / minute / IP** |
| All other routes | 60 requests / minute / IP |

The limiter is instantiated in `app/limiter.py` (a standalone module) to avoid circular imports between `main.py` and `routes/mto.py`.

---

## 9. Security & Secret Management

* **`.env` is git-ignored** — `backend/.gitignore` explicitly excludes `.env` and `*.env` while allowing `.env.example`.
* **`.env.example`** contains only placeholder empty values — no real keys are ever committed.
* `jobs.db` and its WAL files (`-shm`, `-wal`) are also git-ignored.
* API keys are loaded exclusively via `pydantic-settings` from the environment — never hardcoded.

---

## 10. Observability & Health

### Structured Logging

Configured in `app/main.py` via `logging.config.dictConfig`. Format is human-readable `dev` by default; swap the handler formatter to `json` for production:

```
2026-07-07 06:21:02 [INFO] app.store | Job store initialized at 'jobs.db'
2026-07-07 06:21:06 [INFO] app.routes.mto | Job abc-123 accepted (file='drawing.pdf', size=204800 bytes)
2026-07-07 06:21:08 [INFO] app.routes.mto | Extraction started (provider=gemini)
2026-07-07 06:21:14 [INFO] app.routes.mto | Extraction completed successfully
```

All extraction log records include `job_id` via `logging.LoggerAdapter`.

### Health Endpoint

```json
GET /api/health
{
  "status": "ok",
  "version": "0.1.0",
  "provider": "gemini",
  "uptime_s": 143.2,
  "jobs_total": 17
}
```

---

## 11. Sample Drawings & Test Assets

The repository contains two sets of drawing assets used for manual testing, visual regression checks, and vision AI pipeline validation. These files represent the **Questions** (raw inputs/blueprints) and their corresponding **Results** (expected parsed UI dashboard outputs).

### 📂 Backend Sample Drawings (`backend/sample_drawings/`)
These drawings are used to test the end-to-end web application by uploading blueprints directly via the browser upload zone:
* [sample_iso.png](file:///home/msi/Documents/project/backend/sample_drawings/sample_iso.png): A standard 6" carbon steel process line isometric drawing containing common piping items.
* [3. Marked isometric (1).pdf](file:///home/msi/Documents/project/backend/sample_drawings/3.%20Marked%20isometric%20(1).pdf): An annotated, multi-component isometric PDF file with multiple piping runs and callouts.

### 🧪 Regression & Visual Test Assets (`assets/tests/`)
These dedicated testing assets are used as benchmark cases to validate both the backend extraction accuracy and the frontend dashboard visual representation.

#### 1. Test Case 1: Standard Piping Spool
* **Question (Input blueprint):** [test1.png](file:///home/msi/Documents/project/assets/tests/test1.png)
  * *Description:* A standard isometric drawing containing carbon steel piping, multiple $90^\circ$ elbows, reducing tees, support shoes, and inline valve symbols.
  * *Key Characteristics:*
    * Line Number: `USERDEFINEDLINE-3-100-CS300` (8" Nominal Size, class CS300).
    * High-density annotations for supports (labeled `[1]` to `[8]`).
    * Clear weld dots marking shop/field connections.
* **Result (Expected visual dashboard):** [test1_result.jpeg](file:///home/msi/Documents/project/assets/tests/test1_result.jpeg)
  * *Description:* A screenshot of the frontend results workspace showing how `test1.png` should be parsed and rendered.
  * *UI & Data Features Shown:*
    * **Side-by-Side Panel:** The left panel renders the uploaded drawing [test1.png](file:///home/msi/Documents/project/assets/tests/test1.png), while the right panel renders the interactive parsed MTO table.
    * **MTO Item Breakdown:** Correctly displays the main 8" piping run and 4" branch runs, standard fittings (e.g. 90 Deg LR Elbows, Reducing Tees), valves (Gate Valve), and supports.
    * **Programmatic Derivation:** Shows that joints consumable items (Gaskets and Stud Bolts) are derived automatically based on flanged connections and ratings.
    * **Summary Chips:** Total pipe length, fittings, flanges, and valves count cards populated at the top of the workspace.

#### 2. Test Case 2: Complex Geometry & Distinct Title Block
* **Question (Input blueprint):** [test2.png](file:///home/msi/Documents/project/assets/tests/test2.png)
  * *Description:* A second, distinct isometric blueprint sheet with different text orientations, varying label placements, and a custom title block structure. It provides a more challenging geometry for the Vision AI model.
* **Result (Expected visual dashboard):** [test2_result.jpeg](file:///home/msi/Documents/project/assets/tests/test2_result.jpeg)
  * *Description:* The corresponding frontend dashboard screenshot demonstrating successful extraction. It validates that the UI remains visually consistent, components align correctly under standard color schemes, and the table dynamically displays metadata.

---

### 🛠️ CLI Testing & Validation Tool (`backend/test_images.py`)
To validate the backend vision AI pipeline (preprocessing, Gemini API calls, schema validation, and joint consumables derivation) without launching the web servers, you can run the CLI testing script:

```bash
cd backend
source .venv/bin/activate
python test_images.py
```

This runs the active extractor (e.g., Llama NIM or Google Gemini API) directly against [test1.png](file:///home/msi/Documents/project/assets/tests/test1.png) and [test2.png](file:///home/msi/Documents/project/assets/tests/test2.png). Below is an example of successful console output when using the `gemini` extractor:

```text
2026-07-07 18:17:13,533 [INFO] app.services.gemini_extractor: GeminiExtractor initialized with model: gemini-2.5-flash

--- Processing test1.png with gemini ---
Reading file: ../assets/tests/test1.png...
Step 1: Preprocessing image/PDF...
Preprocessing complete. Base64 payload size: 116083 characters.
Step 2: Sending request to extraction provider (gemini)...
Note: Vision extraction can take 10-60+ seconds depending on API response time.
2026-07-07 18:17:25,117 [INFO] app.services.gemini_extractor: Gemini API request attempt 1/3 (model: gemini-2.5-flash)
2026-07-07 18:17:57,622 [INFO] app.services.gemini_extractor: Gemini response received in 32.51s
Extraction successful! Completed in 32.51 seconds.
Step 3: Validating schema and deriving components...
Validation successful.

=== EXTRACTION RESULTS ===
Metadata: drawing_no='Unknown' revision='Unknown' line_number='USERDEFINEDLINE-3-100-CS300' nps='8"' material_class='CS300' service='Unknown' design_pressure=None design_temperature=None
Items:
  1: 8.317 M PIPE | 8" | Pipe, Seamless | None | Remarks: Main line pipe segments (200 NS)
  2: 100.0 M PIPE | 4" | Pipe, Seamless | None | Remarks: Branch line pipe segment (100 NS)
  3: 6.0 EA FITTING | 8" | 90 Deg LR Elbow, BW, ASME B16.9 | None | Remarks: Identified as items 2, 3, 4, 10, 11 on drawing (200 NS)
  4: 1.0 EA FITTING | 8"x4" | Reducing Tee, BW, ASME B16.9 | None | Remarks: Identified as item 5 on drawing (200x100 NS)
  5: 1.0 EA VALVE | 4" | Gate Valve, BW, ASME B16.34 | None | Remarks: Identified as item 9 on drawing (100 NS)
  6: 8.0 EA SUPPORT | 8" | Pipe Support | None | Remarks: Numbered supports [1] through [8]
  7: 19.0 EA WELD | 8" | Butt Weld | None | Remarks: Counted explicit weld symbols on drawing
Summary: total_pipe_length_m=108.32 fittings=7 flanges=0 valves=1 gaskets=0 bolt_sets=0 field_welds=19 supports=8
==========================
```

### 👁️ Frontend & Visual Regression Testing
Developers can use [test1_result.jpeg](file:///home/msi/Documents/project/assets/tests/test1_result.jpeg) and [test2_result.jpeg](file:///home/msi/Documents/project/assets/tests/test2_result.jpeg) to verify:
1. **Responsive Layouts:** Ensure that the side-by-side splits and tables behave correctly on different viewport widths.
2. **Typography & Styling:** Confirm custom component fonts, spacing, shadows, and glassmorphism elements match the design system.
3. **Data Integrity:** Check that MTO tables align correctly, headers are properly capitalized, and units (M, EA, SET) are rendered properly in the UI.

---

## 12. Assumptions, Limitations & Accuracy Strategy

### What the pipeline gets right

* Identifying standard pipe runs and reading labelled lengths from the title block and dimension callouts.
* Counting distinct inline symbols (flanges, valves, elbows) when they appear as clear, isolated standard symbols on the isometric grid.
* Reading title block metadata (drawing number, revision, line number, NPS, material class, service, design conditions).
* Correctly deriving GASKET and BOLT quantities from detected flanged joints — this is deterministic, not LLM-guessed.

### Where it fails

* **Missing BOMs**: For drawings without explicit BOM tables, the pipeline relies on symbol counting, which is inherently lower-confidence without a trained custom detection model. The AI may miss symbols or misinterpret intersecting lines as fittings.
* **Dense or hand-drawn drawings**: Very crowded isometrics with overlapping labels and non-standard symbol styles reduce detection accuracy significantly.
* **Rotated or small text**: Labels smaller than ~6pt or rotated > 30° are often missed or misread by general-purpose vision LLMs.
* **Multi-sheet PDFs**: Only page 1 is processed. Multi-sheet spools are not combined.
* **Non-standard symbols**: Vendor-specific or project-specific symbol libraries not conforming to ISO 10628 may be misclassified.
* **Consumable heuristics**: Gasket/bolt derivation assumes standard flanged joints. Mating equipment (pumps, vessels, special fittings) that introduce additional joints are not modelled.

### Known technical limitations

* **Single-page PDF processing** — page 2+ are silently ignored.
* **No persistent user sessions** — all jobs are anonymous and identified only by UUID.
* **In-process background tasks** — `FastAPI BackgroundTasks` run in the same process. Under very high concurrency, a proper task queue (Celery + Redis) would be needed.

---

## 13. What We Would Improve With More Time

| Priority | Improvement | Rationale |
| :--- | :--- | :--- |
| High | **Celery + Redis task queue** | Replace `BackgroundTasks` with a proper worker for horizontal scalability and task visibility. |
| High | **Hybrid OCR + visual pipeline** | Run PaddleOCR/Tesseract to extract the drawing's built-in BOM table, then reconcile against vision model detections for much higher accuracy. |
| Medium | **Symbol bounding-box overlays** | Return bounding box coordinates for detected components so the frontend can highlight them on the drawing image when a row is hovered. |
| Medium | **Excel export** | Use `openpyxl` to produce formatted `.xlsx` files with company headers, auto-fitted columns, and colour-coded confidence levels. |
| Medium | **Auth & multi-tenancy** | API key or JWT authentication so multiple users can have isolated job histories. |
| Low | **OpenTelemetry + Grafana** | Replace Python logging with distributed tracing across request, background task, and LLM call spans. |
| Low | **Redis/PostgreSQL job store** | Replace SQLite for multi-instance deployments behind a load balancer. |
| Low | **Multi-sheet PDF** | Process all pages of a PDF and merge MTOs, de-duplicating common items by piece mark. |

---

## 14. Backend Engineering Notes

### Circular Import Resolution

`slowapi`'s `Limiter` instance is defined in `app/limiter.py` — a standalone module imported by both `app/main.py` (to wire exception handlers) and `app/routes/mto.py` (to decorate endpoints). This prevents the `ImportError: cannot import name 'limiter' from partially initialized module` that would occur if the limiter were defined in `main.py`.

### Async Safety

| Operation | Method | Reason |
| :--- | :--- | :--- |
| `preprocess_to_base64` (PIL, PyMuPDF) | `asyncio.to_thread` | CPU-bound — blocks for 100–500 ms |
| `extractor.extract` (httpx sync client) | `asyncio.to_thread` | Blocking I/O — up to 90 s |
| `store.*` functions | `async def` + `aiosqlite` | Natively async — no thread needed |
| File read (`await file.read`) | Built-in FastAPI async | Native async upload |

### Job Status Lifecycle

```
POST /api/upload
       │
       ▼
   PENDING  ──── stored immediately, job_id returned to client
       │
       ▼  (background task starts)
   RUNNING
       │
  ┌────┴────┐
  ▼         ▼
COMPLETED FAILED
```

---

## 15. API Reference — MTO JSON Schema

```jsonc
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "COMPLETED",
  "source": "gemini",           // "nvidia" | "gemini" | "openrouter" | "mock"
  "drawing_meta": {
    "drawing_no": "ISO-1501-01",
    "revision": "2",
    "line_number": "6\"-P-1501-A1A-IH",
    "nps": "6\"",
    "material_class": "A1A",
    "service": "Process",
    "design_pressure": "1.6 MPa",
    "design_temperature": "120 C"
  },
  "items": [
    {
      "item_no": 1,
      "category": "PIPE",            // PIPE|FITTING|FLANGE|VALVE|GASKET|BOLT|SUPPORT|WELD
      "description": "Pipe, Seamless, BE, ASME B36.10",
      "size_nps": "6\"",
      "schedule_rating": "SCH 40",
      "material_spec": "ASTM A106 Gr.B",
      "end_type": "BW",              // BW|SW|THD|FLGD|null
      "quantity": 12.45,
      "unit": "M",                   // M (pipe) | EA (discrete) | SET (bolts)
      "length_m": 12.45,             // PIPE only
      "confidence": 0.95,
      "remarks": ""
    }
  ],
  "summary": {
    "total_pipe_length_m": 12.45,
    "fittings": 5,
    "flanges": 2,
    "valves": 1,
    "gaskets": 3,
    "bolt_sets": 3,
    "field_welds": 0,
    "supports": 2
  },
  "image_b64": "data:image/jpeg;base64,…",
  "created_at": "2026-07-07T00:51:06Z",
  "completed_at": "2026-07-07T00:51:14Z"
}
```

---

## 16. Running Tests

```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

The backend contains several meaningful tests to ensure the integrity of the extraction logic:
- **Schema validation**: Verifies that the Pydantic models correctly catch missing fields, enforce allowed categories, and accurately compute gasket/bolt derivations.
- **Endpoint happy-path with the mock pipeline**: Tests the full `POST /api/upload` and `GET /api/mto/{job_id}` cycle without requiring an actual LLM API key, ensuring graceful degradation works.
- **Unit normalization checks**: Ensures that the `validator.py` correctly maps `PIPE` to metres and `FITTING` to counts.

Full coverage is not expected for this assessment, but these critical paths are strictly tested.

> **Note:** Ensure you are running `pytest` from within the activated virtual environment (`source .venv/bin/activate`) so that the internal `app` module resolves correctly.