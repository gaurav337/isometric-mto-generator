# Tasks - Isometric MTO Generator

## Part 1: Project Scaffold, Env Config, Domain Schemas, Mock Pipeline
- `[x]` Create root project `README.md` skeleton
- `[x]` Create `backend/requirements.txt`
- `[x]` Create `backend/.env.example`
- `[x]` Create `backend/app/config.py` settings loader
- `[x]` Create `backend/app/schemas.py` domain schemas (Pydantic)
- `[x]` Create `backend/app/store.py` in-memory job store
- `[x]` Create `backend/app/services/mock_extractor.py` and mock payload
- `[x]` Create `backend/app/routes/mto.py` router and endpoint stubs
- `[x]` Create `backend/app/main.py` entrypoint and CORS config
- `[x]` Run manual verification for Part 1 endpoints
- `[x]` Update root `README.md` to reflect Part 1 completion

## Part 2: AI Pipeline (Pre-processor, Extractor Factory, NVIDIA/Gemini & Validation)
- `[x]` Create `backend/app/services/preprocessor.py` for image normalization
- `[x]` Create `backend/app/services/extractor.py` interface and factory
- `[x]` Create `backend/app/services/nvidia_extractor.py`
- `[x]` Create `backend/app/services/gemini_extractor.py`
- `[x]` Create `backend/app/services/validator.py` validation and post-processing logic
- `[x]` Integrate extraction and validation stages in route handlers
- `[x]` Verify E2E extraction on real drawings (NVIDIA primary, Gemini backup)
- `[x]` Update root `README.md` to document the AI Pipeline

## Part 3: Frontend setup (Next.js, File Upload & MTO viewer)
- `[x]` Scaffold Next.js App Router in `frontend/`
- `[x]` Add frontend TypeScript types and API wrappers
- `[x]` Build drag-and-drop `UploadZone` component with client-side checks
- `[x]` Build `results/[jobId]` page layout
- `[x]` Build MTO table viewer, summary statistics, and metadata display
- `[x]` Handle all loading, error, empty, and mock states in UI
- `[x]` Update root `README.md` with frontend instructions

## Part 4: Backend tests & final polish
- `[x]` Write schema unit tests (`tests/test_schemas.py`)
- `[x]` Write validation & derivation unit tests (`tests/test_validator.py`)
- `[x]` Write endpoint stubs tests (`tests/test_endpoints.py`)
- `[x]` Polish backend type annotations and add docstrings
- `[x]` Polish frontend components and add SEO tags
- `[x]` Update root `README.md` with tests instructions

## Part 5: Docker Compose, final README & submission ZIP
- `[x]` Add `Dockerfile` for frontend and backend
- `[x]` Add `docker-compose.yml` for unified startup
- `[x]` Bundle small sample drawings in `backend/sample_drawings/`
- `[x]` Finalize root `README.md` with screenshots and project discussion
- `[x]` Package project into `<name>_isometric_mto.zip` conforming to restrictions
