# Hematology Lab Reports — CBC / Haematology Analyzer Digitizer

A full-stack web app that digitizes and generates hematology (CBC / fully
automated haematology analyzer) lab reports, replacing a manual paper workflow.

**Stack**
- Frontend: Next.js (App Router) + TypeScript + Tailwind CSS
- Backend: Python FastAPI + SQLite (SQLAlchemy)
- REST API with JSON payloads; CORS enabled for the Next.js origin

## Quick Start

### 1. Backend (FastAPI + SQLite)

```bash
cd backend
python -m venv ../.venv
../.venv/Scripts/pip install -r requirements.txt
../.venv/Scripts/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

The SQLite database (`labreports.db`) and its tables are created automatically
on first run.

### 2. Frontend (Next.js)

```bash
cd frontend
npm install
npm run dev      # serves http://localhost:3000
```

### 3. One-click (Windows)

Double-click `start.bat` at the project root — it starts both servers in
separate windows.

| Service   | URL                        |
|-----------|----------------------------|
| Frontend  | http://localhost:3000      |
| Backend   | http://127.0.0.1:8000      |
| API docs  | http://127.0.0.1:8000/docs |

**Demo login:** `technician` / `lab123` (single lab-technician auth).

## Core Flow

1. **Login** (`/login`) — single technician account.
2. **New Report** (`/new-report`) — enter patient details (or pick an existing
   patient), report metadata (date, referring doctor, technologist), and the
   haematology panel.
3. **Results entry** — parameters grouped into WBC / RBC / Platelet panels.
   Each row has result, unit, reference range, and an auto-flag (High=red,
   Low=blue, Normal=green). Tooltips explain each parameter in plain language.
4. **Auto-calculation** — HCT, MCH, and MCHC are computed from related values
   but can be manually overridden. Reference ranges auto-adjust for
   pediatric (<14) vs adult patients.
5. **Save → View/Print** (`/reports/[id]`) — a professional, printable report
   with lab header, patient block, results table, WBC/RBC/PLT histogram
   placeholders, and a technologist signature line. Export to PDF.
6. **Dashboard** (`/`) — searchable, filterable list of saved reports with
   view / edit / delete actions.

## API Endpoints

`/auth/login` — single-technician authentication (Bearer token).

Patients:
- `POST /patients` — create patient (auto-generates Patient ID like `PT-000001`)
- `GET /patients` — list all
- `GET /patients/{id}` — get one

Reports:
- `POST /reports` — create report + results in one call (auto-generates
  per-day Sample ID like `S-20260902-001`)
- `GET /reports?q=` — list/search (name, patient ID, sample ID)
- `GET /reports/{id}` — get one
- `PUT /reports/{id}` — update report/results
- `DELETE /reports/{id}` — delete
- `GET /reports/{id}/pdf` — download PDF report (reportlab)
- `GET /reports/queue/review` — list reports pending pathologist review
- `POST /reports/{id}/verify` — pathologist sign-off (`reviewed` / `revised`)

## Device Connectivity

The system can ingest results directly from haematology analyzers, in
addition to manual entry.

**Protocols supported**
- **HL7 v2.x** — parses MSH / PID / OBR / OBX segments; extracts patient
  (PID-3 ID, PID-5 name, PID-7 DOB, PID-8 sex) and individual result
  parameters with value, units, reference range, and abnormal flag. Can also
  generate outbound ORU^R01 messages.
- **ASTM E1394** — parses frame structure, computes the 3-digit checksum, and
  interprets H / P / R / L records (including the ENQ/ACK/NAK/EOT handshake
  characters). Can generate outbound frames.

**Transport**
- **TCP/IP socket listener** (`listener.py`) — accepts MLLP or raw/ASTM framed
  messages on a configurable IP/port (default `0.0.0.0:5000`). Persistent
  listener with per-connection threads, timeouts, and reconnect logic.
- **RS-232 serial** — optional serial listener (needs `pyserial`, configurable
  via `serial_port` / `serial_baud`).

**Ingestion pipeline**
- The listener parses a message, maps analyzer parameter IDs to canonical keys,
  upserts the patient, and posts a report to the REST API. Errors on malformed
  or incomplete messages are logged and reported (ACK/NAK).

**Result verification**
- Auto-verified when all results are within range.
- Automatically flagged `pending_review` when any result is abnormal
  (H/L/critical) and queued for the pathologist.
- `/review` page lists the queue; the pathologist can approve/release or mark
  revised with notes.

**Try it (simulate a device)**
```bash
cd backend
python simulate_device.py hl7    # send an HL7 ORU^R01 via MLLP
python simulate_device.py astm   # send an ASTM E1394 batch
```
Start the listener with `start.bat --listener`, then run the simulator to see
the report auto-appear in the dashboard / review queue.

Listen with a different address/port or serial settings via
`listener/listener_config.json` or `LISTENER_*` environment variables
(`LISTENER_HOST`, `LISTENER_PORT`, `LISTENER_PROTOCOL`, `LISTENER_SERIAL_PORT`,
`LISTENER_SERIAL_BAUD`, `LISTENER_PANEL`, …).

## Database Schema (SQLite)

- **patients**: id, first_name, last_name, gender, age, patient_id (unique), created_at
- **reports**: id, patient_id (FK), sample_id, test_date, requested_by,
  technologist_name, comments, verification_status, verification_notes,
  reviewed_by, reviewed_at, source, created_at
- **results**: id, report_id (FK), parameter_name, result_value, unit,
  ref_range_low, ref_range_high, flag (H/L/normal)

## Supported Panels

Two WBC differential formats are supported:
- **Lymph / Mid / Gran** — classic 3-part diff
- **Neu / Lymph / Mono / Eoso / Baso** — 5-part diff

## Nice-to-have features included

- Pediatric vs adult reference ranges (age < 14 uses pediatric defaults)
- Auto-calculated derived indices (HCT, MCH, MCHC) with manual override
- Histogram placeholders on the printable report