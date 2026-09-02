"""ASTM E1394 message parsing and generation for interfacing with analyzers.

ASTM E1394 defines a point-to-point protocol with a frame structure:
    STX <frame-type> <sequence> <fields...> <checksum> ETX

Standard frame types:
    H  - Header (host/analyzer IDs)
    P  - Patient info
    O  - Order / test request
    R  - Results
    C  - Comment
    L  - Terminator (logical record, not a physical frame)

Physical layer handshake uses SOH/ENQ/ACK/NAK/EOT, but many analyzers present
frames as:  \\x02<type>|<seq>|...|<checksum>\\x03

Key capabilities:
  - Parse a stream of ASTM frames into records.
  - Interpret P (patient) and R (result) records into our patient/result model.
  - Generate outbound ASTM frames (e.g. to acknowledge / send a query).
  - Compute the E1384 checksum (3-digit ASCII sum mod 256).
"""

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

STX = "\x02"
ETX = "\x03"
EOT = "\x04"
ENQ = "\x05"
ACK = "\x06"
NAK = "\x15"
LF = "\x0a"
CR = "\x0d"


def astm_checksum(record_body: str) -> str:
    """Compute the 3-digit ASCII checksum for an ASTM record body."""
    total = sum(ord(c) for c in record_body)
    return f"{total % 256:03d}"


def strip_astm_framing(raw: bytes) -> bytes:
    """Remove STX/ETX and CR/LF framing, returning the record body with checksum."""
    return raw.replace(b"\x02", b"").replace(b"\x03", b"").replace(b"\x0d", b"").replace(b"\x0a", b"")


@dataclass
class ASTMRecord:
    """A single ASTM data record: frame type + sequence + fields."""

    frame_type: str
    sequence: int
    fields: List[str]
    raw_body: str = ""

    def field(self, index: int) -> str:
        """1-based field access (ASTM fields start at index 1)."""
        return self.fields[index - 1] if 0 < index <= len(self.fields) else ""


def extract_frames(raw: bytes) -> List[ASTMRecord]:
    """Extract ASTM records from raw bytes, validating checksums."""
    records: List[ASTMRecord] = []
    if isinstance(raw, str):
        raw = raw.encode("latin-1")
    # Normalize: some senders separate with CR or CRLF
    body = raw.replace(b"\x0d\x0a", b"\x0d").replace(b"\x0a", b"\x0d")
    # Split into frames by finding STX boundaries
    frames = body.split(STX.encode())[1:]  # drop leading empty
    for frame in frames:
        # frame = <data><checksum>ETX
        # remove trailing ETX and/or CR
        frame = frame.split(ETX.encode())[0].rstrip(b"\x0d\x0a")
        try:
            text = frame.decode("latin-1")
        except UnicodeDecodeError:
            continue
        if not text:
            continue
        rec = _parse_record_text(text)
        if rec:
            records.append(rec)
    return records


def _parse_record_text(text: str) -> Optional[ASTMRecord]:
    """Parse '<type>|<seq>|...fields...|<checksum>' (checksum already stripped)."""
    if not text:
        return None
    # ASTM records: frame-type char, then '|', seq, '|', fields...
    # The checksum (3 digits) is the final token before ETX, already removed.
    parts = text.split("|")
    if not parts:
        return None
    frame_type = parts[0][:1]  # e.g. 'H', 'P', 'O', 'R', 'L', 'C'
    seq = 0
    try:
        seq = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        seq = 0
    # remaining fields (parts[2:]) are the data fields
    fields = parts[2:]
    return ASTMRecord(frame_type=frame_type, sequence=seq, fields=fields, raw_body=text)


def _split_field(field: str):
    """ASTM components are separated by '^'."""
    return field.split("^")


@dataclass
class ASTMResult:
    """A single parsed ASTM result (from an R-record)."""

    parameter_id: str
    name: str
    value: str
    unit: str
    ref_low: Optional[str]
    ref_high: Optional[str]
    flag_code: str


def parse_astm_results(records: List[ASTMRecord]) -> Dict[str, any]:
    """Interpret P and R records into patient + results."""
    result: Dict[str, any] = {
        "patient_id": "",
        "first_name": "",
        "last_name": "",
        "sex": "",
        "dob": "",
        "results": [],
    }
    for rec in records:
        if rec.frame_type in ("P", "p"):
            # ASTM P-record: P|seq|....|patient_id|...|name|...
            # Fields (after seq): lab no, ref no, LAST^FIRST^MIDDLE, ...,
            #   ... , SEX, DOB ...
            # Heuristic: name is typically LAST^FIRST (first comp = last name).
            result["patient_id"] = rec.field(2) or rec.field(1)
            name_field = _split_field(rec.field(3)) if rec.field(3) else []
            if name_field:
                result["last_name"] = name_field[0]
                if len(name_field) >= 2:
                    result["first_name"] = name_field[1]
            result["sex"] = rec.field(6) or rec.field(8) or ""
            result["dob"] = rec.field(5) or rec.field(7) or ""
        elif rec.frame_type in ("R", "r"):
            # ASTM R-record: R|seq|analyte|value|unit|refs|flag|...
            #   field(1)=analyte (id^name^panel), field(2)=value,
            #   field(3)=unit, field(4)=reference range, field(5)=flag
            analyte = _split_field(rec.field(1))
            param_id = analyte[0] if analyte else ""
            name = analyte[1] if len(analyte) > 1 else param_id
            value = rec.field(2)
            unit = rec.field(3)
            ref = rec.field(4)
            ref_low, ref_high = _parse_ref_range(ref)
            flag = rec.field(5) or rec.field(6)
            result["results"].append(
                ASTMResult(param_id, name, value, unit, ref_low, ref_high, flag)
            )
    return result


def _parse_ref_range(ref: str) -> tuple:
    if not ref:
        return None, None
    ref = ref.strip()
    mm = re.match(r"^([\d.]+)\s*-\s*([\d.]+)", ref)
    if mm:
        return mm.group(1), mm.group(2)
    m2 = re.match(r"^>=?([\d.]+)", ref)
    if m2:
        return m2.group(1), None
    m3 = re.match(r"^<=?([\d.]+)", ref)
    if m3:
        return None, m3.group(1)
    return None, None


# ---------------------------------------------------------------------------
# Outbound ASTM generation
# ---------------------------------------------------------------------------

def build_astm_header(sender: str, receiver: str) -> bytes:
    """Build an ASTM H-record: H|seq|sender|receiver|..||asterisk||E1394|||"""
    body = f"H|1|{sender}||{receiver}|||||1|||"
    chk = astm_checksum(body)
    frame = f"{STX}{body}{chk}{ETX}{CR}{LF}".encode("latin-1")
    return frame


def build_astm_ack(sequence: int = 1) -> bytes:
    """Build an ASTM acknowledgement frame (optional; analyzers use ACK char)."""
    body = f"A|{sequence}|0"
    chk = astm_checksum(body)
    return f"{STX}{body}{chk}{ETX}{CR}{LF}".encode("latin-1")