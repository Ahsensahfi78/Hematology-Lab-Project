"""Ingestion pipeline: parse an incoming message and store it via the REST API.

The pipeline:
  1. Detect transport framing and protocol (HL7 vs ASTM).
  2. Parse into patient + results.
  3. Map analyzer parameter IDs to canonical keys.
  4. Build a patient (reuse by external patient id if possible) and a report
     with results, posting to the FastAPI backend.
"""

import json
import re
from typing import Dict, List, Optional
from urllib import request, parse

from .hl7 import parse_hl7, extract_patient, extract_order, extract_results
from .astm import extract_frames, parse_astm_results
from .mapper import normalize_ident, is_known

# ---------------------------------------------------------------------------
# Numeric parsing
# ---------------------------------------------------------------------------

def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    s = s.replace(",", ".")
    try:
        f = float(s)
        if f != f:  # NaN
            return None
        return f
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Protocol dispatch
# ---------------------------------------------------------------------------

def detect_protocol(raw: bytes) -> str:
    """Return 'hl7' or 'astm' based on framing/content."""
    if isinstance(raw, str):
        raw = raw.encode("latin-1")
    text = raw.decode("latin-1", errors="ignore")
    # ASTM frames are STX-delimited with checksum/ETX
    if "\x02" in text or "|1|" in text and "MSH" not in text:
        return "astm"
    if re.search(r"MSH\|", text):
        return "hl7"
    return "hl7"


def parse_message(raw: bytes) -> Dict:
    """Parse an incoming message into {patient, order, results} dict form."""
    if isinstance(raw, str):
        raw = raw.encode("latin-1")
    proto = detect_protocol(raw)
    if proto == "astm":
        frames = extract_frames(raw)
        data = parse_astm_results(frames)
        results = []
        for r in data["results"]:
            key = normalize_ident(r.parameter_id, r.name)
            results.append(
                {
                    "parameter_name": key,
                    "identifier": r.parameter_id,
                    "name": r.name,
                    "result_value": _to_float(r.value),
                    "unit": r.unit,
                    "ref_range_low": _to_float(r.ref_low),
                    "ref_range_high": _to_float(r.ref_high),
                    "flag_code": r.flag_code,
                }
            )
        return {
            "protocol": "astm",
            "patient": {
                "patient_id": data["patient_id"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "sex": data["sex"],
                "dob": data["dob"],
            },
            "order": {},
            "results": results,
        }

    # HL7
    msg = parse_hl7(raw.decode("latin-1"))
    patient = extract_patient(msg.pid())
    order = extract_order(msg.obr_list()[0] if msg.obr_list() else None)
    obx_results = extract_results(msg)
    results = []
    for r in obx_results:
        key = normalize_ident(r.parameter_id, r.name)
        results.append(
            {
                "parameter_name": key,
                "identifier": r.parameter_id,
                "name": r.name,
                "result_value": _to_float(r.value),
                "unit": r.unit,
                "ref_range_low": _to_float(r.ref_low),
                "ref_range_high": _to_float(r.ref_high),
                "flag_code": r.abnormal_flag,
            }
        )
    return {
        "protocol": "hl7",
        "message_type": msg.message_type(),
        "patient": patient,
        "order": order,
        "results": results,
    }


# ---------------------------------------------------------------------------
# API client used by the listener
# ---------------------------------------------------------------------------

class APIClient:
    def __init__(self, base_url: str, token: str = ""):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _post(self, path: str, payload: Dict) -> Optional[Dict]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = request.Request(url, data=data, headers=self._headers(), method="POST")
        try:
            with request.urlopen(req, timeout=15) as resp:
                body = resp.read()
                if not body:
                    return None
                return json.loads(body.decode("utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def login(self, username: str, password: str) -> bool:
        res = self._post("/auth/login", {"username": username, "password": password})
        if res and "token" in res:
            self.token = res["token"]
            return True
        return False

    def find_patient_by_external_id(self, external_id: str) -> Optional[Dict]:
        try:
            url = f"{self.base_url}/patients"
            req = request.Request(url, headers=self._headers(), method="GET")
            with request.urlopen(req, timeout=15) as resp:
                patients = json.loads(resp.read().decode("utf-8"))
            for p in patients:
                if p.get("patient_id") == external_id:
                    return p
        except Exception:
            pass
        return None

    def create_patient(self, payload: Dict) -> Optional[Dict]:
        return self._post("/patients", payload)

    def create_report(self, payload: Dict) -> Optional[Dict]:
        return self._post("/reports", payload)


# ---------------------------------------------------------------------------
# Pipeline orchestration (used by the listener)
# ---------------------------------------------------------------------------

_DEFAULT_GENDER = "Male"
_DEFAULT_AGE = 30


def _gender_from_sex(sex: str) -> str:
    if not sex:
        return _DEFAULT_GENDER
    s = sex.strip().upper()
    if s in ("F", "FEMALE", "2"):
        return "Female"
    if s in ("M", "MALE", "1"):
        return "Male"
    if s == "UNKNOWN" or s == "U":
        return _DEFAULT_GENDER
    return _DEFAULT_GENDER


def _age_from_dob(dob: str) -> int:
    if not dob:
        return _DEFAULT_AGE
    from datetime import datetime

    # try common formats YYYYMMDD, YYYY-MM-DD
    for fmt in ("%Y%m%d", "%Y-%m-%d", "%Y/%m/%d"):
        try:
            bd = datetime.strptime(dob.strip()[:10], fmt)
            now = datetime.now()
            return max(0, now.year - bd.year - ((now.month, now.day) < (bd.month, bd.day)))
        except ValueError:
            continue
    return _DEFAULT_AGE


def results_payload_from_parsed(parsed: Dict, panel: str = "LMG") -> List[Dict]:
    """Convert parsed raw results into the report `results` payload list,
    keeping only recognized parameters and deriving a flag."""
    out = []
    # map by canonical key, prefer provided ref range or defaults
    from ..references import compute_flag, default_ref_for

    gender = _gender_from_sex(parsed["patient"].get("sex", ""))
    age = _age_from_dob(parsed["patient"].get("dob", ""))
    used = set()
    for r in parsed.get("results", []):
        key = r.get("parameter_name") or ""
        if not key or not is_known(key) or key in used:
            continue
        used.add(key)
        low = r.get("ref_range_low")
        high = r.get("ref_range_high")
        unit = r.get("unit") or ""
        # fill refs from defaults if the device didn't supply
        if low is None and high is None:
            dlow, dhigh = default_ref_for(key, age, gender)
            low = low if low is not None else dlow
            high = high if high is not None else dhigh
        value = r.get("result_value")
        flag = r.get("flag_code") or compute_flag(value, low, high)
        out.append(
            {
                "parameter_name": key,
                "result_value": value,
                "unit": unit,
                "ref_range_low": low,
                "ref_range_high": high,
                "flag": "normal" if flag in ("normal", "N", "") else flag,
            }
        )
    return out


def ingest_parsed(client: APIClient, parsed: Dict, panel: str = "LMG") -> Dict:
    """Persist a parsed message: upsert patient then create a report."""
    patient_info = parsed.get("patient", {})
    external_id = patient_info.get("patient_id") or ""

    # Try to reuse an existing patient by matching external patient_id.
    patient = client.find_patient_by_external_id(external_id) if external_id else None
    if patient is None:
        # age derived from DOB for reference ranges
        patient = client.create_patient(
            {
                "first_name": patient_info.get("first_name") or "Unknown",
                "last_name": patient_info.get("last_name") or "Patient",
                "gender": _gender_from_sex(patient_info.get("sex", "")),
                "age": _age_from_dob(patient_info.get("dob", "")),
            }
        )
        if not patient or "error" in (patient or {}):
            return {"error": f"Could not create patient: {patient}"}

    results = results_payload_from_parsed(parsed, panel)
    if not results:
        return {"error": "No recognized results to save"}

    order = parsed.get("order", {})
    report = client.create_report(
        {
            "patient_id": patient["id"],
            "requested_by": order.get("requested_by") or "",
            "technologist_name": "",
            "panel_type": panel,
            "source": parsed.get("protocol", "") or "",
            "comments": f"Auto-ingested {parsed.get('protocol', '').upper()} message",
            "results": results,
        }
    )
    return report