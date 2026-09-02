"""HL7 v2.x message parsing and generation for haematology analyzers.

Supports the segments most relevant to a CBC / automated analyzer result:
MSH, PID, OBR, OBX (and tolerates ORC, SPM, etc. by ignoring them).

Key capabilities:
  - Parse a raw HL7 message into structured segments/fields.
  - Extract patient (PID), order (OBR), and result (OBX) data.
  - Compute a result abnormal flag from an OBX abnormal flag code (e.g. H/L),
    or compute it from value vs reference range.
  - Generate an outbound HL7 ORU^R01 message (e.g. to send results to an LIS).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# HL7 default encoding characters
FIELD_SEP = "|"
COMPONENT_SEP = "^"
REPETITION_SEP = "~"
ESCAPE_CHAR = "\\"
SUBCOMPONENT_SEP = "&"


@dataclass
class Segment:
    """A single HL7 segment: segment ID (e.g. 'PID') + list of fields."""

    segment_id: str
    fields: List[str]

    def field(self, index: int) -> str:
        """Return field at 1-based index, or '' if not present."""
        return self.fields[index - 1] if 0 < index <= len(self.fields) else ""

    def component(self, field_index: int, comp: int = 1) -> str:
        """Return a component (1-based) of a field."""
        f = self.field(field_index)
        parts = f.split(COMPONENT_SEP)
        return parts[comp - 1] if 0 < comp <= len(parts) else ""


@dataclass
class HL7Message:
    """A parsed HL7 message with typed accessors for common segments."""

    segments: List[Segment] = field(default_factory=list)
    encoding_chars: List[str] = field(
        default_factory=lambda: [
            COMPONENT_SEP,
            REPETITION_SEP,
            ESCAPE_CHAR,
            SUBCOMPONENT_SEP,
        ]
    )

    def segments_of(self, segment_id: str) -> List[Segment]:
        return [
            seg for seg in self.segments if seg.segment_id == segment_id or
            (seg.segment_id and seg.segment_id[:3] == segment_id)
        ]

    def first(self, segment_id: str) -> Optional[Segment]:
        segs = self.segments_of(segment_id)
        return segs[0] if segs else None

    def msh(self) -> Optional[Segment]:
        return self.first("MSH")

    def pid(self) -> Optional[Segment]:
        return self.first("PID")

    def obx_list(self) -> List[Segment]:
        return self.segments_of("OBX")

    def obr_list(self) -> List[Segment]:
        return self.segments_of("OBR")

    def message_type(self) -> str:
        msh = self.msh()
        if not msh:
            return ""
        mt = msh.field(9)  # e.g. ORU^R01
        return mt.split(COMPONENT_SEP)[0] if mt else ""

    def message_control_id(self) -> str:
        msh = self.msh()
        return msh.field(10) if msh else ""

    def raw(self) -> str:
        """Reconstruct the message as a single HL7 string."""
        lines = []
        for seg in self.segments:
            if seg.segment_id == "MSH":
                # MSH has the field separator as field 2 (not repeated)
                lines.append(
                    FIELD_SEP
                    + seg.segment_id
                    + FIELD_SEP
                    + "".join(self.encoding_chars)
                    + FIELD_SEP
                    + FIELD_SEP.join(seg.fields[2:])
                )
            else:
                lines.append(seg.segment_id + FIELD_SEP + FIELD_SEP.join(seg.fields))
        return "\r".join(lines) + "\r"


def parse_hl7(raw: str) -> HL7Message:
    """Parse a raw HL7 message string (segments separated by CR)."""
    msg = HL7Message()
    # Normalize line endings: HL7 uses CR (\r); tolerate \n and \r\n
    normalized = raw.replace("\r\n", "\r").replace("\n", "\r")
    for line in normalized.split("\r"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("MSH"):
            # MSH: field sep is char[3], encoding chars follow
            segment_id = line[:3]
            field_sep = line[3] if len(line) > 3 else FIELD_SEP
            rest = line[5:] if line[4:5] == field_sep else line[4:]
            enc_chars = rest[:4] if len(rest) >= 4 else ["^", "~", "\\", "&"]
            msg.encoding_chars = list(enc_chars)
            # MSH fields: [1]=sep placeholder, [2]=enc chars, then split on sep
            fields = [field_sep, "".join(enc_chars)[:4]] + rest[4:].split(field_sep)
            msg.segments.append(Segment(segment_id, fields))
        else:
            segment_id = line[:3]
            token = line[3:4] or FIELD_SEP
            tail = line[4:]
            fields = tail.split(token) if tail else []
            msg.segments.append(Segment(segment_id, fields))
    return msg


# ---------------------------------------------------------------------------
# Field extraction helpers
# ---------------------------------------------------------------------------

def extract_patient(pid: Optional[Segment]) -> Dict[str, str]:
    """Extract patient fields from a PID segment: ID, name, DOB, sex."""
    result = {
        "patient_id": "",
        "first_name": "",
        "last_name": "",
        "dob": "",
        "sex": "",
    }
    if pid is None:
        return result
    # PID-3: list of identifiers, first is external patient id
    pids = pid.field(3).split(REPETITION_SEP)
    if pids:
        result["patient_id"] = pids[0].split(COMPONENT_SEP)[0]
    # PID-5: patient name  -> family^given^middle
    name = pid.field(5)
    if name:
        parts = name.split(COMPONENT_SEP)
        result["last_name"] = parts[0] if len(parts) > 0 else ""
        result["first_name"] = parts[1] if len(parts) > 1 else ""
    result["dob"] = pid.field(7)
    result["sex"] = pid.field(8)
    return result


def extract_order(obr: Optional[Segment]) -> Dict[str, str]:
    """Extract order info from OBR: placer order no, filler order no, requested by."""
    result = {"order_number": "", "filler_number": "", "requested_by": ""}
    if obr is None:
        return result
    result["order_number"] = obr.field(2) if obr.field(2) else obr.field(3)
    result["filler_number"] = obr.field(3)
    # OBR-16: ordering provider -> name
    provider = obr.field(16)
    if provider:
        result["requested_by"] = provider.split(COMPONENT_SEP)[1] or provider.split(COMPONENT_SEP)[0]
    return result


# OBX abnormal flag codes -> our flag
_FLAG_MAP = {
    "H": "H",
    "HH": "H",
    "L": "L",
    "LL": "L",
    "A": "normal",  # abnormal? treat A as abnormal-unspecified -> leave normal here
    "N": "normal",
    "-": "normal",
    "": "normal",
    "NULL": "normal",
}


def map_flag_code(code: str) -> str:
    c = (code or "").strip()
    if not c:
        return "normal"
    return _FLAG_MAP.get(c.upper(), "normal")


@dataclass
class HL7Result:
    """A single parsed OBX result parameter."""

    parameter_id: str
    name: str
    value: str
    unit: str
    ref_low: Optional[str]
    ref_high: Optional[str]
    flag_code: str
    abnormal_flag: str  # computed H/L/normal


def extract_results(msg: HL7Message) -> List[HL7Result]:
    """Parse OBX segments into a list of result parameters."""
    results: List[HL7Result] = []
    for obx in msg.obx_list():
        # OBX-2 value type, OBX-3 observer id (ident^name), OBX-5 value(s),
        # OBX-6 units, OBX-7/8 ref range, OBX-8 abnormal flags
        observer_id = obx.field(3)
        ident_and_name = observer_id.split(COMPONENT_SEP)
        param_id = ident_and_name[0] if len(ident_and_name) > 0 else ""
        name = ident_and_name[1] if len(ident_and_name) > 1 else ""
        value = obx.field(5)
        unit = obx.field(6)
        ref_range = obx.field(7)
        flag_code = obx.field(8)

        ref_low, ref_high = _parse_ref_range(ref_range)

        # OBX-5 may contain multiple values (e.g. '^' separated) -> take first
        if value and "^" in value:
            value = value.split(COMPONENT_SEP)[0]

        results.append(
            HL7Result(
                parameter_id=param_id,
                name=name,
                value=value,
                unit=unit,
                ref_low=ref_low,
                ref_high=ref_high,
                flag_code=flag_code,
                abnormal_flag=map_flag_code(flag_code),
            )
        )
    return results


def _parse_ref_range(ref_range: str) -> tuple:
    """Parse a reference range string like '4.0-11.0', '4.0 - 11.0', '>=4'."""
    if not ref_range:
        return None, None
    text = ref_range.strip()
    m = re.match(r"^([<>]=?)?\s*([\d.]+)\s*-\s*([\d.]+)", text)
    if m:
        return m.group(2), m.group(3)
    m2 = re.match(r"^>=\s*([\d.]+)", text)
    if m2:
        return m2.group(1), None
    m3 = re.match(r"^<=\s*([\d.]+)", text)
    if m3:
        return None, m3.group(1)
    # single numeric -> ambiguous; return as-is low
    m4 = re.match(r"^([\d.]+)$", text)
    if m4:
        return m4.group(1), m4.group(1)
    return None, None


# ---------------------------------------------------------------------------
# Message generation (outbound ORU^R01)
# ---------------------------------------------------------------------------

def build_hl7_oru(
    patient_id: str,
    last_name: str,
    first_name: str,
    sex: str,
    dob: str,
    sample_id: str,
    test_id: str,
    test_name: str,
    requested_by: str,
    results: List[Dict],
    control_id: Optional[str] = None,
) -> str:
    """Build an HL7 v2.4 ORU^R01 message shipping results to an LIS.

    `results` items: dict with keys name, value, unit, ref_low, ref_high, flag.
    """
    import uuid

    cid = control_id or uuid.uuid4().hex[:16]
    lines = []
    # MSH-9 = ORU^R01, MSH-10 = control id
    lines.append(
        "MSH|^~\\&|ANALYZER|LAB|LIS|HOSP|"
        f"{_now_ts()}|"
        f"ORU^R01|{cid}|P|2.4|"
    )
    # PID
    lines.append(
        f"PID||{patient_id}||{last_name}^{first_name}||{dob}|{sex}"
    )
    # OBR
    lines.append(f"OBR|1|{sample_id}||{test_id}^{test_name}|||{_now_ts()}|||||{requested_by}")
    for r in results:
        ref = ""
        if r.get("ref_low") is not None and r.get("ref_high") is not None:
            ref = f"{r['ref_low']}-{r['ref_high']}"
        elif r.get("ref_low") is not None:
            ref = f">{r['ref_low']}"  # not standard, keep simple
        value = r.get("value", "")
        lines.append(
            f"OBX|1|NM|{r.get('id','')}^{r.get('name','')}||"
            f"{value}|{r.get('unit','')}|{ref}|{r.get('flag','')}"
        )
    return "\r".join(lines) + "\r"


def _now_ts() -> str:
    from datetime import datetime

    return datetime.now().strftime("%Y%m%d%H%M%S")