# Implementation Plan: Isometric Drawing → Automated MTO Generator
### Full-Stack AI Engineering Assessment · Next.js + FastAPI + Vision AI Pipeline

---

> [!IMPORTANT]
> **This plan is broken into 5 parts executed sequentially. Each part ends with a README.md update step. Do not move to the next part until the current part is complete and verified.**

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    MONOREPO LAYOUT                          │
│  project/                                                   │
│  ├── frontend/          (Next.js 14 · App Router)           │
│  ├── backend/           (FastAPI · Python 3.11+)            │
│  │   ├── app/                                               │
│  │   │   ├── main.py         (FastAPI app + CORS + routes)  │
│  │   │   ├── config.py       (pydantic-settings env loader) │
│  │   │   ├── schemas.py      (all Pydantic domain models)   │
│  │   │   ├── routes/                                        │
│  │   │   │   └── mto.py      (upload / status / csv)       │
│  │   │   ├── services/                                      │
│  │   │   │   ├── extractor.py      (interface + factory)   │
│  │   │   │   ├── nvidia_extractor.py                       │
│  │   │   │   ├── gemini_extractor.py                       │
│  │   │   │   ├── mock_extractor.py                         │
│  │   │   │   ├── preprocessor.py   (PDF→image, resize)     │
│  │   │   │   └── validator.py      (derive + reconcile)    │
│  │   │   └── store.py         (in-memory job store)        │
│  │   ├── tests/                                             │
│  │   │   ├── test_schemas.py                               │
│  │   │   ├── test_validator.py                             │
│  │   │   └── test_endpoints.py                             │
│  │   ├── requirements.txt                                  │
│  │   ├── .env.example                                      │
│  │   └── sample_drawings/   (1-2 small sample ISOs)        │
│  ├── README.md            (root, always kept up-to-date)   │
│  └── docker-compose.yml   (bonus)                          │
└─────────────────────────────────────────────────────────────┘
```

**Key design decisions (document all in README):**
- **App Router** (Next.js 14) — not Pages Router. Reason: App Router enables React Server Components and native streaming, which fits a "process then display" flow better. Pages Router is simpler but legacy.
- **Synchronous `POST /api/extract`** — not async job queue. Reason: Single image per upload, latency acceptable for this scope. Job queue only earns complexity for batch/multi-sheet work (out of scope). Trade-off documented in README.
- **One interface, two configs** for AI providers — not two separate code paths. Both NVIDIA Build and Gemini expose OpenAI-compatible chat completions. One `VisionExtractor` base class, three concrete implementations (NVIDIA, Gemini, Mock), selected by factory at startup based on env keys. No parallel code paths.
- **Deterministic post-processing, not LLM-trust** — unit normalization, gasket/bolt derivation, summary recomputation are all deterministic Python. The LLM is trusted only for entity identification (what exists, roughly what size), not for domain-critical rules.

---

## Part 1 — Project Scaffold, Env Config, Domain Schemas, Mock Pipeline

> **Goal:** A fully-runnable backend with mock data, correct schemas, and initial README. No AI calls yet. After this part, `POST /api/upload` works end-to-end with mock data and Swagger docs are live.

### 1.1 Repository & Directory Structure

**Create the following directories:**
```
project/
├── backend/
│   ├── app/
│   │   ├── routes/
│   │   ├── services/
│   │   └── __init__.py (empty)
│   ├── tests/
│   └── sample_drawings/
├── frontend/        ← empty for now, created in Part 3
└── README.md        ← skeleton created now
```

No files beyond directory structure and the files below at this stage.

---

### 1.2 `backend/.env.example`

```
# AI Provider Keys — set ONE or BOTH. NVIDIA is tried first.
# If neither is set, the app falls back to the mock pipeline.
NVIDIA_API_KEY=your_nvidia_build_api_key_here
NVIDIA_MODEL=meta/llama-3.2-11b-vision-instruct
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1

GEMINI_API_KEY=your_google_ai_studio_key_here
GEMINI_MODEL=gemini-2.5-flash

# Server
HOST=0.0.0.0
PORT=8000

# CORS — set to your frontend URL
FRONTEND_URL=http://localhost:3000
```

> [!IMPORTANT]
> **Model name correction:** The correct NVIDIA Build NIM model for free-tier vision with structured output support is `meta/llama-3.2-11b-vision-instruct` (or `90b` variant). The `llama-3-vision-70b` name referenced in the brief does not exist on NIM. This is documented as a deliberate assumption in the README.

---

### 1.3 `backend/requirements.txt`

```
fastapi>=0.110.0
uvicorn>=0.28.0
pydantic>=2.6.0
pydantic-settings>=2.2.0
openai>=1.14.0           # used for BOTH NVIDIA NIM and as OpenAI-compatible client
google-generativeai>=0.5.0
httpx>=0.27.0
pymupdf>=1.24.0          # PDF → image rendering (PyMuPDF / fitz)
python-multipart>=0.0.9  # FastAPI multipart file upload
python-dotenv>=1.0.1
pytest>=8.0.0
pytest-asyncio>=0.23.0
Pillow>=10.0.0           # image processing / resize
```

---

### 1.4 `backend/app/config.py`

Use `pydantic-settings` `BaseSettings`. Fields:
- `nvidia_api_key: str | None = None`
- `nvidia_model: str = "meta/llama-3.2-11b-vision-instruct"`
- `nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"`
- `gemini_api_key: str | None = None`
- `gemini_model: str = "gemini-2.5-flash"`
- `host: str = "0.0.0.0"`
- `port: int = 8000`
- `frontend_url: str = "http://localhost:3000"`
- `max_file_size_mb: int = 20`

`model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")`

Expose a single `get_settings()` function using `@lru_cache` for singleton behavior.

---

### 1.5 `backend/app/schemas.py` — The Complete Domain Model

This is the most important file in the backend. Every field must be correct per Section 2 of the spec.

**Enums:**
```python
class ItemCategory(str, Enum):
    PIPE = "PIPE"
    FITTING = "FITTING"
    FLANGE = "FLANGE"
    VALVE = "VALVE"
    GASKET = "GASKET"
    BOLT = "BOLT"
    SUPPORT = "SUPPORT"
    WELD = "WELD"

class ItemUnit(str, Enum):
    M = "M"      # metres — PIPE only
    EA = "EA"    # each — FITTING, FLANGE, VALVE, SUPPORT, WELD
    SET = "SET"  # set — BOLT (one set = all studs+nuts for one joint)

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
```

**`DrawingMetadata`:**
- `drawing_no: str`
- `revision: str`
- `line_number: str` — e.g. `"6\"-P-1501-A1A-IH"`
- `nps: str` — e.g. `"6\""`
- `material_class: str`
- `service: str`
- `design_pressure: str | None`
- `design_temperature: str | None`

**`MTOItem`:**
- `item_no: int`
- `category: ItemCategory` — strict enum, never free string
- `description: str` — full ASME vocab description e.g. `"90° LR Elbow, BW, ASME B16.9"`
- `size_nps: str` — regex validator: `r'^\d+(\.\d+)?"(x\d+(\.\d+)?")?$'` — supports reducing e.g. `"6\"x4\""`
- `schedule_rating: str | None` — `"SCH 40"` / `"CL150"` etc.
- `material_spec: str | None` — `"ASTM A106 Gr.B"` etc.
- `end_type: str | None` — BW / SW / THD / FLGD
- `quantity: float` — count for discrete items, length for PIPE
- `unit: ItemUnit` — **derived post-hoc, never trusted from model**: PIPE→M, BOLT→SET, else EA
- `length_m: float | None` — Pydantic validator: required when `category == PIPE`, rejected/set to None otherwise
- `confidence: float | None` — 0.0 to 1.0
- `remarks: str` — default `""`

**`MTOSummary`:**
- `total_pipe_length_m: float` — computed by summing PIPE rows, never from model output
- `fittings: int`
- `flanges: int`
- `valves: int`
- `gaskets: int`
- `bolt_sets: int`
- `field_welds: int`
- `supports: int`

**`MTOResponse`:**
- `job_id: str`
- `status: JobStatus`
- `source: Literal["nvidia", "gemini", "mock"]` — surfaced in UI as a badge
- `drawing_meta: DrawingMetadata | None`
- `items: list[MTOItem]`
- `summary: MTOSummary | None`
- `error_message: str | None`
- `created_at: datetime`
- `completed_at: datetime | None`

**`UploadResponse`:** `{ job_id: str, status: JobStatus }`

**`ErrorResponse`:** `{ detail: str, code: str }`

---

### 1.6 `backend/app/store.py` — In-Memory Job Store

Simple Python dict keyed by `job_id` (UUID4 string) → `MTOResponse`. No database needed.

```python
_jobs: dict[str, MTOResponse] = {}

def create_job(job_id: str) -> MTOResponse: ...
def get_job(job_id: str) -> MTOResponse | None: ...
def update_job(job_id: str, data: MTOResponse) -> None: ...
```

---

### 1.7 `backend/app/services/mock_extractor.py` — MockExtractor

Returns a fully realistic MTO built from a bundled sample drawing. This is the fallback when no API keys are present. This is a **designed code path, not a crash guard.**

Key requirements:
- The returned `MTOResponse` has `source="mock"` and a clearly labeled remark like `"[MOCK DATA — no API key configured]"`.
- The mock data must be realistic: correct ASME descriptions, proper material specs, proper size/schedule, correct units, and derived gaskets/bolts.
- The mock's raw pre-derivation output must be a static fixture usable directly in backend unit tests (so tests never touch the network).

Sample mock data structure — include at minimum:
- 1 PIPE row with `length_m`
- 2–3 FITTING rows (90° elbow, tee)
- 2 FLANGE rows (→ triggers 2 gaskets + 2 bolt sets in derivation)
- 1 VALVE row (flanged → triggers 1 more gasket + 1 bolt set)
- Derived GASKET and BOLT rows

---

### 1.8 `backend/app/main.py` — FastAPI App Shell

- Init `FastAPI(title="Isometric MTO API", version="0.1.0")`
- Add `CORSMiddleware` with `allow_origins=[settings.frontend_url]`, `allow_methods=["*"]`, `allow_headers=["*"]`
- Include router from `routes/mto.py`
- Add `/api/health` directly: `{"status": "ok", "provider": "mock|nvidia|gemini"}`

---

### 1.9 `backend/app/routes/mto.py` — Endpoint Stubs (Mock-backed)

All endpoints implemented, all backed by mock extractor for now:

**`POST /api/upload`**
- Validates: `content_type` in `["image/png", "image/jpeg", "application/pdf"]`
- Validates: file size ≤ `settings.max_file_size_mb` MB (server-side, independent of client)
- Creates a job in store with `status=PENDING`
- Calls the extractor synchronously (mock at this stage)
- Updates job to `COMPLETED` or `FAILED`
- Returns `UploadResponse`

**`GET /api/mto/{job_id}`**
- Returns the `MTOResponse` from store
- Returns 404 with `ErrorResponse` if not found

**`GET /api/mto/{job_id}/csv`**
- Builds a CSV from `MTOResponse.items` using Python `csv` module
- Returns `StreamingResponse` with `Content-Disposition: attachment; filename=mto_{job_id}.csv`
- Columns: `item_no, category, description, size_nps, schedule_rating, material_spec, end_type, quantity, unit, length_m, confidence, remarks`

---

### 1.10 README.md — Part 1 Update

After Part 1 is complete, add to `README.md`:
- Project overview paragraph
- ASCII architecture diagram
- Directory structure tree
- Python version requirement (3.11+)
- Backend setup commands:
  ```
  cd backend
  python -m venv .venv
  .venv\Scripts\activate   # Windows
  pip install -r requirements.txt
  cp .env.example .env
  uvicorn app.main:app --reload
  ```
- Note: "At this stage, no API key is needed — the app runs with mock data."

---

### Part 1 Verification

- `uvicorn app.main:app --reload` starts without errors
- `http://localhost:8000/docs` shows all 4 endpoints with correct request/response schemas
- `POST /api/upload` with a PNG file returns a job_id, status=COMPLETED, source="mock"
- `GET /api/mto/{job_id}` returns the full mock MTO with all required fields
- `GET /api/mto/{job_id}/csv` returns a downloadable CSV with correct columns
- `GET /api/health` returns `{"status": "ok", "provider": "mock"}`

---

## Part 2 — AI Pipeline: Pre-processor, Extractor Interface, NVIDIA + Gemini Implementations

> **Goal:** Real AI extraction works. Factory selects provider from env. One retry on schema failure, then falls through to structured error. README updated with pipeline architecture section.

### 2.1 `backend/app/services/preprocessor.py` — Pre-processing Stage

Converts any input (PDF or image) to a base64-encoded JPEG string suitable for the vision LLM.

Steps:
1. **File type detection:** read first bytes (magic bytes), not trusting the `Content-Type` header alone.
2. **PDF → image:** Use `pymupdf` (`fitz`). Render page 0 at 150 DPI. Convert to RGB. If multi-page PDF, process only page 0 for now (document multi-sheet as a "with more time" improvement).
3. **Image normalization:**
   - Convert to RGB if RGBA or grayscale.
   - Resize: if width or height > 2048px, scale down proportionally. Reason: vision model context limits and token cost.
   - No aggressive compression — keep enough resolution that small text (dimensions, line numbers) remains readable.
4. **Base64 encode:** return a `data:image/jpeg;base64,...` string.
5. **Error handling:** if `pymupdf` fails or image is corrupt, raise `PreprocessingError` (custom exception) that the route handler catches and returns as 422 with `ErrorResponse`.

---

### 2.2 `backend/app/services/extractor.py` — Interface + Factory

**Abstract base class `VisionExtractor`:**
```python
from abc import ABC, abstractmethod

class VisionExtractor(ABC):
    @abstractmethod
    def extract(self, image_b64: str) -> dict:
        """Returns raw dict matching MTOResponse schema before Pydantic validation."""
        ...

    @property
    @abstractmethod
    def source(self) -> str: ...
```

**Factory function `get_extractor(settings) -> VisionExtractor`:**
```python
def get_extractor(settings: Settings) -> VisionExtractor:
    if settings.nvidia_api_key:
        return NvidiaExtractor(settings)
    elif settings.gemini_api_key:
        return GeminiExtractor(settings)
    else:
        return MockExtractor()
```

This factory is called **once at startup** and injected into route handlers via FastAPI dependency injection (`Depends`). No repeated env lookups per request.

---

### 2.3 The Extraction Prompt — Core of Domain Understanding

This prompt is **part of the deliverable**. The evaluators will read it. It must use correct piping vocabulary from Section 2 of the spec.

**System message (sent once):**
```
You are a piping engineering AI assistant specializing in reading piping isometric drawings 
and extracting Material Take-Offs (MTOs). A piping isometric is a 2D engineering drawing 
representing a 3D pipe run on an isometric axis system (120° between axes; vertical lines 
stay vertical; horizontal runs at 30°).

You will receive an image of an isometric drawing. Your task is to identify and list every 
material component present:
- PIPE: straight pipe segments. Quantify by total cut length in metres.
- FITTING: elbows (90°/45°, LR/SR), tees (equal/reducing), reducers (concentric/eccentric), 
  caps, couplings, olets. Governed by ASME B16.9 (BW) or B16.11 (SW/THD).
- FLANGE: weld-neck (WN), slip-on (SO), blind (BL), socket-weld (SW). ASME B16.5. 
  Drawn as perpendicular ticks on the pipe line.
- VALVE: gate (plain bowtie), globe (bowtie+dot), check (bowtie+flap), ball (bowtie+circle), 
  butterfly. Usually flanged. Class-rated.
- SUPPORT: shoes, guides, anchors, hangers. Tagged PS-xx.

DO NOT emit GASKET or BOLT rows — these will be derived programmatically.

For each item, use exact ASME/ASTM material vocabulary:
- Carbon steel pipe: ASTM A106 Gr.B (seamless)
- CS butt-weld fittings: ASTM A234 WPB
- CS forged flanges/fittings: ASTM A105
- SS pipe: ASTM A312 TP316L
- SS forged: ASTM A182 F316L

Size: use NPS in inches (e.g. "6\""). For reducing items: "6\"x4\"".
Schedule: "SCH 40", "SCH 80", "STD", "XS", "XXS".
Pressure class for flanges/valves: "CL150", "CL300", "CL600".
End type: "BW" (butt-weld), "SW" (socket-weld), "THD" (threaded), "FLGD" (flanged).

Read the title block for drawing_no, revision, line_number, nps, material_class, service.
Read dimension callouts to sum pipe lengths. 1 metre = 1000 mm.

Assign confidence 0.0-1.0 per item based on how clearly you can see it in the drawing.
If the drawing is unclear or you cannot read a field, use null for that field.
```

**User message per request:**
```
Please analyze this piping isometric drawing and extract the complete MTO.
Return ONLY a valid JSON object matching the provided schema. No prose, no markdown fences.
```

---

### 2.4 `backend/app/services/nvidia_extractor.py` — NvidiaExtractor

- Uses `openai.OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)`
- Model: `settings.nvidia_model` (default `meta/llama-3.2-11b-vision-instruct`)
- Message format: `role="user"` with `content=[{"type": "image_url", "image_url": {"url": image_b64}}, {"type": "text", "text": user_prompt}]`
- Response format: `{"type": "json_object"}` — NIM structured output. Attempt `json_schema` response format first; fall back to `json_object` if unsupported by model.
- Timeout: 90 seconds
- **One retry on JSON parse failure or schema validation failure**, then raise `ExtractionError`
- Return raw parsed `dict` (not Pydantic model — validation happens in the validator stage)

---

### 2.5 `backend/app/services/gemini_extractor.py` — GeminiExtractor

- Uses `google.generativeai` library: `genai.configure(api_key=settings.gemini_api_key)`
- Model: `settings.gemini_model` (default `gemini-2.5-flash`)
- Uses `generation_config={"response_mime_type": "application/json", "response_schema": MTOLLMOutput.model_json_schema()}`
- `MTOLLMOutput` is a flat Pydantic model matching only what the LLM should return (no derived fields like GASKET/BOLT, no job metadata)
- Sends image as `genai.types.Part.from_data(data=image_bytes, mime_type="image/jpeg")`
- Timeout: 90 seconds
- Same one-retry on failure pattern as NVIDIA
- Return raw parsed `dict`

---

### 2.6 `backend/app/services/validator.py` — Post-processing / Derivation

This is the highest-value, most testable logic in the entire system.

**Step 1: Unit normalization (overwrite, don't trust LLM)**
```python
UNIT_MAP = {
    ItemCategory.PIPE: ItemUnit.M,
    ItemCategory.BOLT: ItemUnit.SET,
}
for item in items:
    item.unit = UNIT_MAP.get(item.category, ItemUnit.EA)
```

**Step 2: `length_m` enforcement**
- If `category == PIPE` and `length_m is None` or `length_m <= 0`: log warning, set `length_m = 0.0`, set `confidence` lower.
- If `category != PIPE` and `length_m is not None`: set `length_m = None`.

**Step 3: `size_nps` normalization**
- Strip whitespace, ensure inch symbol present.
- Validate against regex: `r'^\d+(\.\d+)?"(x\d+(\.\d+)?")?$'`
- If invalid: set to original string with a remark flag (don't drop the item entirely).

**Step 4: Gasket + Bolt derivation (domain rule)**
```
Rule: 1 GASKET + 1 BOLT SET per flanged joint.
Flanged joints = count(FLANGE rows) + count(VALVE rows where end_type == "FLGD" or category == "VALVE")
```
Reconciliation logic:
1. Count existing GASKET rows from LLM output.
2. Count existing BOLT rows from LLM output.
3. Required = flange_count + flanged_valve_count
4. If existing_gaskets < required: append `(required - existing_gaskets)` GASKET rows
5. If existing_bolts < required: append `(required - existing_bolts)` BOLT rows
6. Use material_spec from the flanges in the same NPS for material context.

Document in README: *"GASKET and BOLT rows are always derived programmatically from flange and flanged-valve counts, per the 1-per-joint rule. LLM output for these categories is ignored to prevent double-counting."*

**Step 5: Summary recomputation**
Always compute `MTOSummary` from the validated, derived item list — never from model's own summary block:
```python
total_pipe_length_m = sum(i.length_m for i in items if i.category == PIPE and i.length_m)
fittings = sum(i.quantity for i in items if i.category == FITTING)
flanges = sum(i.quantity for i in items if i.category == FLANGE)
valves = sum(i.quantity for i in items if i.category == VALVE)
gaskets = sum(i.quantity for i in items if i.category == GASKET)
bolt_sets = sum(i.quantity for i in items if i.category == BOLT)
field_welds = sum(i.quantity for i in items if i.category == WELD and "FW" in i.remarks)
```

If model's summary `total_pipe_length_m` disagrees with computed value by > 5%: add a remark to the PIPE row: `"[WARNING: LLM reported X m, computed Y m — computed value used]"`. Surface this discrepancy in the UI as a QA signal.

**Step 6: Item re-numbering**
Re-number all items sequentially after derivation so `item_no` is always 1, 2, 3...

---

### 2.7 Wire Everything Together in Route Handler

Update `routes/mto.py` `POST /api/upload`:
1. Validate file (type + size)
2. Read bytes
3. Call `preprocessor.to_base64(bytes, content_type)` → `image_b64`
4. Call `extractor.extract(image_b64)` → raw dict (wraps in try/except, catches ExtractionError)
5. Call `validator.validate_and_derive(raw_dict)` → validated `MTOResponse`
6. Store in job store
7. Return `UploadResponse`

All exceptions map to structured `ErrorResponse`:
- `ValidationError` → 422
- `FileSizeError` → 413
- `FileTypeError` → 415
- `ExtractionError` → 502 (upstream AI failure)
- Generic `Exception` → 500 (never expose stack trace)

---

### 2.8 README.md — Part 2 Update

Add to README:
- **AI Pipeline section** with this diagram:
  ```
  Upload → Pre-process → Extract (NVIDIA/Gemini/Mock) → Validate & Derive → Serve
     |           |                |                              |
  type+size   PDF→JPEG        JSON schema                  unit normalization
  check       resize           constrained                 bolt/gasket derivation
              base64           output                      summary recomputation
  ```
- **Provider selection logic:** "NVIDIA if `NVIDIA_API_KEY` set, else Gemini if `GEMINI_API_KEY` set, else Mock."
- **Model used:** `meta/llama-3.2-11b-vision-instruct` (NVIDIA). Assumption: spec mentions `llama-3-vision-70b` which does not exist on NIM; `llama-3.2-11b-vision-instruct` is the correct free-tier NIM vision model with structured output support.
- **Honest accuracy section:** what works, what fails, what would be next.
  - Will work well: clearly printed BOM tables, distinct symbols, readable title blocks.
  - Will fail/degrade: dense overlapping dimensions, hand-drawn/scanned isos, rotated text at non-standard angles (isometric 30°/120° convention), multiple line numbers per sheet, NVIDIA smaller model struggling with small dense text vs. Gemini.
  - Next steps with more time: fine-tuned symbol detector for bounding boxes, multi-sheet PDF handling, ensemble both providers and reconcile disagreements.

---

### Part 2 Verification

- Set `NVIDIA_API_KEY` in `.env` → `GET /api/health` returns `{"provider": "nvidia"}`
- `POST /api/upload` with a real isometric image → returns MTO with `source="nvidia"`
- Confirm validator correctly sets units (PIPE→M, BOLT→SET)
- Confirm GASKET + BOLT rows are derived from flange count
- Confirm `summary.total_pipe_length_m` is computed from items, not from model
- Remove API keys → falls back to `source="mock"` gracefully (no crash, no 500)

---

## Part 3 — Frontend: Next.js App, Upload UI, Results View

> **Goal:** Full working UI. Upload drawing, see results side-by-side, see summary cards, export CSV. Loading and error states handled everywhere. README updated with frontend setup.

### 3.1 Next.js Project Setup

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app --no-src-dir --import-alias "@/*"
```

**Router choice: App Router.** Reason documented in README.

**Key dependencies to add:**
- `react-dropzone` — drag-and-drop file upload
- `react-hot-toast` — notification toasts for errors
- `@tanstack/react-table` — headless table for MTO display

---

### 3.2 Frontend Env Config

`frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```
`frontend/.env.example` — same with placeholder comment.

---

### 3.3 Page Structure (App Router)

```
frontend/app/
├── layout.tsx          — root layout, fonts, global styles
├── page.tsx            — upload page (root route)
├── results/
│   └── [jobId]/
│       └── page.tsx    — results page
├── components/
│   ├── UploadZone.tsx
│   ├── MTOTable.tsx
│   ├── SummaryCards.tsx
│   ├── DrawingMeta.tsx
│   ├── DrawingPreview.tsx
│   ├── ProviderBadge.tsx  — shows "NVIDIA / Gemini / MOCK" badge
│   ├── LoadingSpinner.tsx
│   └── ErrorBanner.tsx
├── lib/
│   ├── api.ts          — typed fetch wrappers for all backend endpoints
│   └── types.ts        — TypeScript types mirroring backend Pydantic schemas
```

---

### 3.4 `frontend/app/lib/types.ts`

Mirror all backend Pydantic schemas as TypeScript interfaces:

```typescript
export type ItemCategory = "PIPE" | "FITTING" | "FLANGE" | "VALVE" | "GASKET" | "BOLT" | "SUPPORT" | "WELD";
export type JobStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
export type ProviderSource = "nvidia" | "gemini" | "mock";

export interface DrawingMetadata {
  drawing_no: string;
  revision: string;
  line_number: string;
  nps: string;
  material_class: string;
  service: string;
  design_pressure?: string;
  design_temperature?: string;
}

export interface MTOItem {
  item_no: number;
  category: ItemCategory;
  description: string;
  size_nps: string;
  schedule_rating?: string;
  material_spec?: string;
  end_type?: string;
  quantity: number;
  unit: "M" | "EA" | "SET";
  length_m?: number;
  confidence?: number;
  remarks: string;
}

export interface MTOSummary {
  total_pipe_length_m: number;
  fittings: number;
  flanges: number;
  valves: number;
  gaskets: number;
  bolt_sets: number;
  field_welds: number;
  supports: number;
}

export interface MTOResponse {
  job_id: string;
  status: JobStatus;
  source: ProviderSource;
  drawing_meta?: DrawingMetadata;
  items: MTOItem[];
  summary?: MTOSummary;
  error_message?: string;
  created_at: string;
  completed_at?: string;
}

export interface UploadResponse {
  job_id: string;
  status: JobStatus;
}
```

---

### 3.5 `frontend/app/lib/api.ts`

Typed fetch wrappers:
- `uploadDrawing(file: File): Promise<UploadResponse>` — `POST /api/upload`
- `getMTO(jobId: string): Promise<MTOResponse>` — `GET /api/mto/{jobId}`
- `getCSVUrl(jobId: string): string` — returns the CSV download URL (direct link, no fetch needed)

All functions: typed response, typed error (`ApiError` with `detail: string, code: string`), no untyped `any`.

---

### 3.6 `UploadZone.tsx` Component

- Uses `react-dropzone`: `accept: { "image/png": [], "image/jpeg": [], "application/pdf": [] }`
- **Client-side validation** (per spec):
  - File type check: rejected with clear error message if wrong type
  - File size check: reject if > 20 MB, show specific message
- Shows upload progress bar (fake 0→90% during upload, 100% on response)
- On successful upload: navigates to `/results/[jobId]`
- Error state: shows `ErrorBanner` with the API error detail
- Loading state: shows spinner with "Analyzing drawing..." text

---

### 3.7 `results/[jobId]/page.tsx` — Results Page

Layout: two-column on desktop, stacked on mobile.

**Left column:** `DrawingPreview` — shows the uploaded image. Since we're not storing the file on the backend for return, we use `URL.createObjectURL` from the upload form state. Alternatively, pass the file object via query param or session storage from the upload page. Document approach in README.

**Right column:**
1. `DrawingMeta` — displays all `drawing_meta` fields in a structured card
2. `ProviderBadge` — colored badge: "NVIDIA" (green), "Gemini" (blue), "MOCK" (amber with warning text)
3. `SummaryCards` — 6 cards: Total Pipe Length, Fittings, Flanges, Valves, Gasket Sets, Bolt Sets
4. CSV export button: anchor tag pointing to `GET /api/mto/{jobId}/csv`, download attribute set
5. `MTOTable` — full MTO table

---

### 3.8 `MTOTable.tsx` Component

Columns (matching spec Section 2.2):
- `#` (item_no)
- `Category` — colored chip per category (PIPE=blue, FITTING=teal, FLANGE=purple, VALVE=orange, GASKET=pink, BOLT=gray)
- `Description`
- `Size NPS`
- `Schedule/Rating`
- `Material Spec`
- `End Type`
- `Qty`
- `Unit`
- `Length (m)` — only non-null for PIPE rows
- `Confidence` — if present, show colored bar (green ≥ 0.8, amber 0.6–0.8, red < 0.6)
- `Remarks`

Features:
- Sortable by category and size
- Striped rows, sticky header
- Mobile: horizontal scroll, columns stay intact

---

### 3.9 Error and Loading States

Every state must be handled — per spec "never show a blank screen or an unhandled crash":

| State | What to show |
|---|---|
| Uploading | Progress bar + spinner |
| Processing (LLM running) | Spinner + "Analyzing your isometric drawing..." |
| Job FAILED | `ErrorBanner` with `error_message` from API |
| Job not found (404) | "Drawing not found" with link back to upload |
| Network error | "Could not connect to backend" toast + retry button |
| Mock mode | Amber `ProviderBadge` + notice banner: "Showing demo data — no API key configured" |

---

### 3.10 README.md — Part 3 Update

Add to README:
- **Frontend setup commands:**
  ```
  cd frontend
  npm install
  cp .env.example .env.local
  npm run dev
  ```
- **Router choice explanation:** App Router chosen for...
- **UI features:** upload, drag-drop, results view, summary cards, CSV export, mock badge
- Note: Node.js version requirement (≥ 18)

---

### Part 3 Verification

- `npm run dev` starts without TypeScript errors
- Upload a PNG → navigates to results page
- Results page shows drawing preview, metadata, summary cards, MTO table
- CSV export downloads a valid CSV
- Mock badge shows when no API key configured
- Reload the results page by URL directly → still works (not a purely client-side route)

---

## Part 4 — Backend Tests & Polish

> **Goal:** Meaningful backend tests that cover validation/derivation logic, schema correctness, and endpoint happy paths. Polish both backend and frontend. README updated with test section.

### 4.1 `backend/tests/test_schemas.py`

Test Pydantic model validation rules:
- Valid `MTOItem` with PIPE category and `length_m` passes
- `MTOItem` with PIPE category and no `length_m` fails validation (or is caught by validator)
- `MTOItem` with VALVE category and `length_m` set → validator sets it to None
- `size_nps` regex: `"6\""` passes, `"6\"x4\""` passes, `"badval"` fails
- `ItemCategory` rejects any string not in enum
- `ItemUnit` derived correctly from category

### 4.2 `backend/tests/test_validator.py`

Test the derivation + reconciliation logic using the MockExtractor's raw output as fixture:
- Unit normalization overwrites LLM-provided units
- Gasket count = flange count + flanged valve count when LLM returns zero gaskets
- Gasket count is NOT doubled when LLM already returned correct number
- Summary `total_pipe_length_m` is sum of PIPE rows regardless of model summary
- Item renumbering is sequential after derivation

### 4.3 `backend/tests/test_endpoints.py`

Test HTTP layer:
- `GET /api/health` returns 200 with `{"status": "ok"}`
- `POST /api/upload` with valid PNG bytes (small fixture) returns 200 with `job_id`
- `GET /api/mto/{job_id}` returns the job data after upload
- `GET /api/mto/nonexistent` returns 404
- `POST /api/upload` with oversized file returns 413
- `POST /api/upload` with wrong file type returns 415
- All tests use `MockExtractor` — no real API calls in test suite

### 4.4 Backend Polish

- Add type hints everywhere (`mypy`-clean)
- Add docstrings to all public functions
- Remove any leftover debug `print` statements
- Confirm Swagger `/docs` has correct descriptions and response examples

### 4.5 Frontend Polish

- Fix any TypeScript `any` types
- Add `<title>` and `<meta description>` tags per page
- Mobile responsive check
- Ensure no unhandled promise rejections in browser console
- Add favicon

### 4.6 README.md — Part 4 Update

Add:
- **Tests section:**
  ```
  cd backend
  pytest tests/ -v
  ```
- List what tests cover and why they were chosen
- Confirm "no API key needed to run tests"

---

### Part 4 Verification

- `pytest tests/ -v` all green, no network calls
- No TypeScript errors in frontend (`npx tsc --noEmit`)
- Swagger `/docs` fully documented

---

## Part 5 — Sample Drawings, Docker Compose, Final README, ZIP Packaging

> **Goal:** Ship-ready submission. Sample drawings included, docker-compose.yml added (bonus), README complete and self-contained. All penalty checklist items verified.

### 5.1 Sample Drawings

- Source 1–2 small (< 500 KB each) public-domain piping isometric drawings.
  - Option A: search "piping isometric drawing example PDF site:engineering.* OR site:*.edu" for public domain samples.
  - Option B: generate a simple hand-drawn/diagrammatic ISO using any tool and export as PNG.
- Place in `backend/sample_drawings/`
- Document in README: "Tested with sample_drawing_01.png (6" process line, carbon steel, 4 elbows, 2 flanges)"

### 5.2 `docker-compose.yml` (Bonus)

```yaml
version: "3.9"
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: ./backend/.env

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
```

Also create `backend/Dockerfile` and `frontend/Dockerfile`.

### 5.3 README.md — Final Complete Version

README must contain **in this order** (per spec Section 5):
1. **Project overview** — 2 paragraphs
2. **Architecture diagram** — ASCII
3. **Exact setup steps** for both backend and frontend (including Python 3.11+, Node 18+)
4. **Environment variables** — every variable, what it does, where to get the key
5. **AI pipeline explanation** — pre-process → extract → validate → serve, with provider selection logic, model names, prompt strategy, mock fallback behavior
6. **Assumptions made:**
   - NVIDIA model `meta/llama-3.2-11b-vision-instruct` used (NIM free tier; `llama-3-vision-70b` in brief does not exist on NIM)
   - Synchronous single-call design chosen (not async job queue) — trade-offs stated
   - Only page 0 processed for multi-page PDFs
   - GASKET and BOLT always derived, LLM output for these categories discarded
   - `size_nps` assumed in inches throughout
7. **Known limitations and honest accuracy discussion:**
   - Dense overlapping dimension lines confuse the model
   - Hand-drawn/scanned isos with inconsistent line weights lose accuracy
   - Rotated BOM-table text at 30°/120° (isometric convention) may not be read correctly
   - Multiple line numbers per sheet: only first identified is used
   - NVIDIA's smaller free vision model (`11b`) will struggle more with small dense text than Gemini (`2.5-flash`) — named explicitly, not hidden
   - No bounding-box overlay — would require fine-tuned detector, noted as next step
8. **What would be improved with more time:**
   - Multi-sheet PDF handling
   - Fine-tuned symbol detector for bounding boxes
   - Ensemble both providers, reconcile disagreements for higher accuracy
   - Async job queue for batch processing
   - Excel export with formatted columns
   - Confidence-aware re-prompting for low-confidence items
9. **Screenshots** (2, compressed JPEG) of working app

### 5.4 Pre-ZIP Checklist

Before zipping, verify each item:

| Check | Status |
|---|---|
| No `node_modules/` in zip | ✓ |
| No `.next/` in zip | ✓ |
| No `venv/` or `.venv/` in zip | ✓ |
| No `__pycache__/` in zip | ✓ |
| No `.git/` in zip | ✓ |
| No real API keys in any file | ✓ |
| `.env.example` present (not `.env`) | ✓ |
| ZIP size ≤ 10 MB | ✓ |
| `README.md` at root | ✓ |
| `frontend/` and `backend/` at root | ✓ |
| App runs end-to-end from README steps on a fresh machine (mock pipeline) | ✓ |
| `/docs` Swagger works | ✓ |
| CSV export works | ✓ |

### 5.5 README.md — Final Update

Add:
- Screenshots section (with embedded compressed images)
- Submission note: "ZIP packaged as `<name>_isometric_mto.zip`"

---

### Part 5 Verification

- Fresh machine test: follow README from scratch, confirm everything works
- `docker-compose up` starts both services (if Docker available)
- ZIP created, size checked ≤ 10 MB

---

## Summary: README Update Rule

> [!IMPORTANT]
> **Every time a new component is created, update `README.md` immediately.** Do not defer README updates to the end. The README is a living document throughout development.

| After Part | README sections added |
|---|---|
| Part 1 | Overview, directory structure, backend setup, mock pipeline note |
| Part 2 | AI pipeline architecture, provider selection, model assumption, accuracy discussion |
| Part 3 | Frontend setup, router choice, UI features |
| Part 4 | Tests section |
| Part 5 | Full final version, screenshots, assumptions, limitations, improvement list |
