Take-Home Assessment · Full-Stack + AI
Isometric Drawing to Automated MTO Generator
Full-Stack AI Engineering Assessment: Next.js · FastAPI · Vision AI Pipeline

Stack (mandatory)	Frontend: Next.js  ·  Backend: FastAPI (Python)
AI provider	NVIDIA Build API (primary, e.g. meta/llama-3-vision-70b-instruct) or Google Gemini API (backup), dynamically selected based on env configuration.
Scope	The app processes one isometric drawing per upload
Deliverable	One single ZIP file containing full source code + README.md setup guide
Size limit	ZIP must be ≤ 10 MB (exclude node_modules/, .next/, venv/, model weights, etc.)
Deadline	8 July, 8:00 AM. Submissions after this time will not be evaluated.
Estimated effort	1 to 2 days
1.Objective
Build a full-stack web application where a user can upload one piping isometric drawing (image or PDF) and the system automatically generates a Material Take-Off (MTO): a structured bill of materials listing every pipe, fitting, flange, valve, gasket and bolt set present on the drawing, using an AI pipeline on the backend.

This assessment evaluates four things:

Full-stack engineering: clean Next.js frontend + FastAPI backend, correct API design, file handling.
AI pipeline design: how you extract structured engineering data from an unstructured drawing (vision LLM, OCR, CV, or a hybrid).
Domain understanding: whether your MTO output reflects a real understanding of what an isometric contains. This document gives you everything you need, so read Section 2 carefully.
Communication: the quality of your README, your assumptions, and your architecture explanation.
Expectation setting
You are not expected to achieve production-grade extraction accuracy in 1 to 2 days. You are expected to build a working end-to-end system with a sensible, well-explained pipeline. You are encouraged to use AI coding assistants (Copilot, ChatGPT, Claude, Cursor) to build faster, as long as you fully understand every line you submit.
2.Domain Knowledge Primer (read this before coding)
You do not need prior piping experience. Everything required is explained below, and we expect your data model and README to use this vocabulary correctly.

2.1 What is an Isometric Drawing?
A piping isometric (commonly called an "iso") is a 2-D engineering drawing that represents a 3-D pipe run. It is drawn on an isometric axis system: the three spatial axes (X, Y, Z) are drawn at 120° to each other (in practice, vertical lines stay vertical and horizontal runs are drawn at 30° to the horizontal). This lets a single flat drawing show routing in all three dimensions without perspective distortion and not to scale. Dimensions are written on the drawing, not measured from it.

Isometrics are the primary fabrication and erection document in the piping industry (oil & gas, petrochemical, power, pharma). Each iso typically covers one pipeline (one "line number") and contains:

The pipe routing: a single-line representation of the pipe with direction changes, drawn on the isometric grid. A "North arrow" indicates plant orientation.
Dimensions: lengths between fittings/welds in mm (or feet-inches), elevation callouts (e.g. EL. +104500), and coordinates.
Symbols for every inline component (see 2.4).
The line number: an identifier encoding size, service, material spec and insulation, e.g. 6"-P-1501-A1A-IH. Here: 6" nominal size, P = process service, 1501 = line sequence, A1A = piping material class/spec, IH = insulation code.
Weld points: shop welds vs field welds (field welds usually marked FW), which matter for fabrication planning.
Spool breaks: an iso is divided into spools, which are pre-fabricated sections welded in a workshop, sized so they can be transported and erected on site.
A Bill of Materials (BOM) table: most real isometrics carry a BOM block (usually top-right or bottom) listing every material item with piece-mark numbers keyed to balloons/callouts on the drawing.
Title block: drawing number, revision, project, line number, sheet number, design pressure/temperature, test pressure, paint/insulation specs.
2.2 What is an MTO (Material Take-Off)?
A Material Take-Off is the structured, quantified list of all materials required to build what a drawing shows. In piping, the MTO is generated per isometric and then rolled up per line / per area / per project for procurement, cost estimation and warehouse control.

A proper piping MTO row typically contains:

Field	Meaning	Example
item_no	Sequential item / piece mark	1, 2, 3...
category	PIPE / FITTING / FLANGE / VALVE / GASKET / BOLT / SUPPORT	FITTING
description	Full engineering description	90° LR Elbow, BW, ASME B16.9
size_nps	Nominal Pipe Size (inches); reducing items have two sizes	6" or 6"x4"
schedule_rating	Wall thickness schedule (pipes/fittings) or pressure class (flanges/valves)	SCH 40 / CL150 / CL300
material_spec	ASTM/ASME material grade	ASTM A106 Gr.B, A234 WPB, A105
end_type	Connection type: BW (butt-weld), SW (socket-weld), THD (threaded), FLGD (flanged)	BW
quantity	Count for discrete items	4
unit	M (metres) for pipe, EA/NO for discrete items, SET for bolts	EA
length_m	Total cut length, pipes only	12.45
remarks	Anything relevant (e.g. "field weld", "by vendor")	-
Key convention
Pipe is quantified by total length, everything else by count. Bolts are counted in sets (one set per flanged joint), gaskets one per flanged joint.
2.3 Why automate it with AI?
Manual MTO extraction from isometrics is slow (10 to 30 minutes per sheet), error-prone, and projects have thousands of sheets. Errors cause material shortages (schedule delays) or over-ordering (cost). Automating "drawing in, structured MTO out" is a real, high-value industry problem. This assessment is a miniature version of it.

2.4 Component glossary & symbols you should handle
Your pipeline should attempt to recognise (or at minimum your data model must support) these component families:

Pipe

Straight pipe segments, identified by line thickness/route; quantified by summed length.
Fittings (change direction / branch / size), governed by ASME B16.9 (butt-weld) or B16.11 (socket-weld/threaded):

Elbow 90° / 45° (LR = long radius, SR = short radius), drawn as a sharp direction change in the route.
Tee (equal / reducing): a branch symbol where a line joins the run.
Reducer (concentric / eccentric): trapezoid symbol where line size changes.
Cap: closed pipe end.
Coupling / Union / Olets (weldolet, sockolet, threadolet): small branch connections.
Flanges, governed by ASME B16.5, rated by class (150/300/600...):

Weld-neck (WN), Slip-on (SO), Blind (BL), Socket-weld (SW) flanges. Symbol: short perpendicular tick or pair of ticks on the line.
Valves, drawn as a "bowtie" (two triangles):

Gate (plain bowtie), Globe (bowtie with solid centre dot), Check (bowtie with flap indication), Ball (bowtie with circle), Butterfly. Usually flanged, with class rating.
Joint consumables (usually not drawn as symbols, but derivable: 1 per flanged joint):

Gasket (e.g. spiral wound, SS316/graphite, ASME B16.20).
Stud bolts with nuts (e.g. ASTM A193 B7 / A194 2H), counted in sets.
Supports (bonus): shoe, guide, anchor, hanger. Often tagged like PS-01.

Instrumentation connections (bonus): pressure/temperature tappings.

Welds: butt welds drawn as dots/dashes on the line; field welds (FW) flagged separately. Weld count is a bonus output.

2.5 Relevant standards vocabulary (use it in descriptions)
ASME B31.3: process piping design code (context).
ASME B16.9: butt-weld fittings; B16.5: flanges; B16.11: forged SW/THD fittings; B16.20: gaskets.
Materials: ASTM A106 Gr.B (carbon steel seamless pipe), A234 WPB (CS butt-weld fittings), A105 (CS forged flanges), A312 TP316L (stainless pipe), A182 F316L (stainless forged).
NPS (Nominal Pipe Size, inches) and Schedule (SCH 10/40/80/160, STD/XS/XXS) define size and wall thickness.
3.Functional Requirements
3.1 Frontend (Next.js, mandatory)
Upload page
Drag-and-drop + file-picker upload for one PNG, JPG, or PDF isometric drawing at a time.
Client-side validation: file type and size (reject > 20 MB), with clear error states.
Upload progress indication and a processing/loading state while the AI pipeline runs.
Results page/panel
A preview of the uploaded drawing side-by-side with the extracted MTO.
The MTO rendered as a table with (at minimum) the columns from Section 2.2.
Summary chips/cards: total pipe length, fitting count, flange count, valve count, bolt/gasket sets.
Extracted drawing metadata: line number, drawing number, revision, size, material class (whatever your pipeline can read from the title block).
Export as CSV (Excel export is a bonus).
If your pipeline returns per-item confidence, show it (color coding or a confidence column). This is a bonus.
General
Sensible loading, empty and error states. It should never show a blank screen or an unhandled crash.
Use the App Router or Pages Router, your choice. Justify it in the README.
Styling is your choice (Tailwind, CSS modules, etc.). We judge clarity and usability, not visual flourish.
3.2 Backend (FastAPI, mandatory)
Endpoints (suggested contract; you may adapt it, document whatever you ship):
POST /api/upload            -> accepts multipart file, returns { job_id }
GET  /api/mto/{job_id}      -> returns processing status + MTO JSON when ready
GET  /api/mto/{job_id}/csv  -> returns the MTO as a CSV download
GET  /api/health            -> liveness check
A synchronous single-call design (POST /api/extract returning the MTO directly) is acceptable for this assessment. State your choice and its trade-offs in the README.

Validation & safety: enforce content-type and size limits server-side; never trust the client.
Auto docs: FastAPI's /docs (Swagger) must work out of the box.
Storage: in-memory or on-disk storage of jobs is fine. No database is required (using SQLite is fine too).
CORS configured so the Next.js dev server can call the API.
3.3 The AI pipeline (the core of the assessment)
The backend must convert the uploaded drawing into the structured MTO. Recommended approach: a vision LLM extraction pipeline using the NVIDIA Build API (primary) with Google Gemini API as a backup, depending on which key is configured in the environment.

AI Providers:
- Primary: NVIDIA Build (NGC API) using a free vision NIM model (e.g. meta/llama-3-vision-70b-instruct or meta/llama-3.1-405b-instruct). Get a free API key at build.nvidia.com.
- Backup: Google AI Studio (Gemini) using a free Gemini API key from aistudio.google.com and a vision model (e.g. gemini-2.5-flash).
Pre-process: normalize the input (PDF to image render, resize/enhance if needed).
Extract: send the drawing to the configured vision LLM with a carefully engineered prompt + strict JSON schema describing the MTO structure.
Post-process / validate: validate the JSON with Pydantic models, normalize units (inches for NPS, metres for length), derive computed items (gasket + bolt set per flanged joint if the LLM didn't), compute summary totals.
Serve: return the validated MTO.
Alternative or hybrid approaches are equally welcome and can score higher if well executed: OCR (Tesseract/PaddleOCR) for the BOM table + title block, classical CV or a small detection model for symbols, or reading the drawing's existing BOM table and reconciling it against symbol detection.

Hard requirements for the pipeline
Pluggable provider: the LLM/API key must come from environment variables (.env.example provided, no keys committed).
Graceful degradation: if no API key is configured, the app must still run end-to-end and return a clearly-labelled mock/sample MTO (so evaluators can run your app without credentials). Do not let a missing key crash the app.
Prompt & schema in the repo: your extraction prompt and JSON schema are part of the deliverable. We will read them. This is where domain understanding shows.
Explain your accuracy strategy in the README: what the pipeline will get right, where it will fail (dense drawings, hand-drawn isos, rotated text), and what you would do next with more time.
3.4 Suggested MTO JSON schema (adapt as needed)
{
  "drawing_meta": {
    "drawing_no": "ISO-1501-01",
    "revision": "2",
    "line_number": "6\"-P-1501-A1A-IH",
    "nps": "6\"",
    "material_class": "A1A",
    "service": "Process"
  },
  "items": [
    {
      "item_no": 1,
      "category": "PIPE",
      "description": "Pipe, Seamless, BE, ASME B36.10",
      "size_nps": "6\"",
      "schedule_rating": "SCH 40",
      "material_spec": "ASTM A106 Gr.B",
      "end_type": "BW",
      "quantity": 1,
      "unit": "M",
      "length_m": 12.45,
      "confidence": 0.92,
      "remarks": ""
    },
    {
      "item_no": 2,
      "category": "FITTING",
      "description": "Elbow 90 Deg LR, BW, ASME B16.9",
      "size_nps": "6\"",
      "schedule_rating": "SCH 40",
      "material_spec": "ASTM A234 WPB",
      "end_type": "BW",
      "quantity": 4,
      "unit": "EA",
      "confidence": 0.88
    }
  ],
  "summary": {
    "total_pipe_length_m": 12.45,
    "fittings": 4,
    "flanges": 2,
    "valves": 1,
    "gaskets": 2,
    "bolt_sets": 2,
    "field_welds": 1
  }
}
4.Non-Functional Requirements
Code quality: typed Python (type hints + Pydantic), typed TypeScript on the frontend. Clear module boundaries (routes / services / pipeline / models).
Error handling: bad file, oversized file, unreadable drawing, LLM timeout/failure. All must return clean, structured error responses that the frontend surfaces.
No secrets in the repo: .env.example only. A committed API key is an automatic significant penalty.
Reproducible setup: a fresh machine must be able to run your app by following the README alone. A docker-compose.yml is a welcome bonus but not required.
Tests: at least a few meaningful backend tests (e.g., schema validation, endpoint happy-path with the mock pipeline). Full coverage is not expected.
5.Deliverables & Submission Rules
Submit exactly one ZIP file, named:

<yourname>_isometric_mto.zip
The ZIP must contain:

Full source code: frontend/ (Next.js) and backend/ (FastAPI). A monorepo layout is fine.
A root README.md containing, in this order:
Project overview + a small architecture diagram (ASCII is fine).
Exact setup steps: every command, for both frontend and backend, including Python/Node version requirements.
Environment variables (.env.example documented).
How the AI pipeline works: pre-processing, extraction, validation, which model/provider, the prompt strategy, and the mock fallback.
Assumptions made and known limitations.
What you would improve with more time.
.env.example (no real keys).
1 or 2 sample isometric drawings you tested with (small files: public-domain, self-drawn, or generated), plus a screenshot or two of the working app (compressed).
Optional: docker-compose.yml, tests, Postman/Bruno collection.
The ZIP must NOT contain
node_modules/, .next/, dist/, venv//__pycache__/, model weights, .git/, or any real API keys. Total size ≤ 10 MB. Oversized or multi-file submissions will not be evaluated.
⏰ Deadline: 8 July, 8:00 AM
No extensions.
6.Evaluation (100 points)
Area	Weight	What we look for
Working end-to-end flow	25	Upload, process, MTO table, CSV export: all working on a fresh machine following the README (with the mock pipeline if we have no key).
AI pipeline design	25	Sensible architecture; structured-output usage; validation layer; graceful fallback; honest accuracy discussion. Prompt & schema quality.
Domain correctness	15	MTO fields, units and conventions match Section 2 (pipe by length, fittings by count, gasket/bolt derivation, size/schedule/material vocabulary).
Backend engineering	12	Clean FastAPI structure, Pydantic models, validation, error handling, API design.
Frontend engineering	12	Clean Next.js structure, usable UI, loading/error states, table + export.
README & communication	8	Setup reproducibility, clear architecture explanation, assumptions & limitations honestly stated.
Tests & polish	3	Meaningful tests, tidy repo.
Bonus (up to +10)	-	Docker Compose; Excel export; confidence visualization; weld counting; bounding-box overlay of detected symbols on the drawing; multi-sheet PDF handling; job queue with async processing.
Automatic penalties
Committed secrets; ZIP > 10 MB or containing node_modules/venv; app crashes on the documented happy path; README steps that don't work.
7.Rules & Clarifications
Use AI coding assistants. Copilot, ChatGPT, Claude, and Cursor are allowed and encouraged. You must fully understand your submission: a follow-up walkthrough interview will cover your design decisions line-by-line, and inability to explain your own code fails the assessment.
Use the NVIDIA Build API (primary) or Google Gemini API (backup). Free API keys from either platform cover everything this assessment needs. No paid services are required.
Third-party libraries are allowed.
If you cannot access any LLM API, submit with the mock pipeline fully working and describe (with the actual prompt you would send) how the real path would work. You can still score well on everything except live extraction.
Sample isometrics can be found by searching for "piping isometric drawing example"; you may also draw or generate your own. Keep bundled samples small.
Questions: email us. Ambiguity you resolve yourself with a documented assumption is also acceptable (and is itself evaluated).
Good luck. We are more interested in how you think (pipeline design, domain modelling, trade-offs) than in pixel-perfect extraction accuracy.