"""Unit tests for HL7 v2.x and ASTM E1394 parsing/generation."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.protocol.hl7 import (
    parse_hl7,
    extract_patient,
    extract_results,
    build_hl7_oru,
    map_flag_code,
)
from app.protocol.astm import (
    astm_checksum,
    extract_frames,
    parse_astm_results,
    build_astm_header,
)
from app.protocol.mapper import normalize_ident, is_known
from app.protocol.ingest import (
    detect_protocol,
    parse_message,
    results_payload_from_parsed,
)
from tests.sample_messages import SAMPLE_HL7, sample_astm


class TestHL7(unittest.TestCase):
    def test_parse_segments(self):
        msg = parse_hl7(SAMPLE_HL7)
        self.assertEqual(len(msg.segments), 11)
        msh = msg.msh()
        self.assertEqual(msh.segment_id, "MSH")
        self.assertEqual(msh.field(9), "ORU^R01")

    def test_extract_patient(self):
        msg = parse_hl7(SAMPLE_HL7)
        pid = msg.pid()
        pat = extract_patient(pid)
        self.assertEqual(pat["last_name"], "JONES")
        self.assertEqual(pat["first_name"], "MARY")
        self.assertEqual(pat["sex"], "F")
        self.assertEqual(pat["dob"], "19781010")

    def test_extract_results(self):
        msg = parse_hl7(SAMPLE_HL7)
        results = extract_results(msg)
        self.assertEqual(len(results), 8)
        wbc = results[0]
        self.assertEqual(wbc.parameter_id, "WBC")
        self.assertEqual(wbc.value, "12.4")
        self.assertEqual(wbc.ref_low, "4.0")
        self.assertEqual(wbc.ref_high, "11.0")
        self.assertEqual(wbc.abnormal_flag, "H")

    def test_flag_map(self):
        self.assertEqual(map_flag_code("H"), "H")
        self.assertEqual(map_flag_code("L"), "L")
        self.assertEqual(map_flag_code("N"), "normal")
        self.assertEqual(map_flag_code(""), "normal")

    def test_generate(self):
        out = build_hl7_oru(
            "PT123", "Doe", "Jane", "F", "19800101", "SP001", "CBC", "CBC", "Dr. A",
            [{"id": "WBC", "name": "WBC", "value": "10.0", "unit": "x10^3/uL",
              "ref_low": "4", "ref_high": "11", "flag": "N"}],
        )
        self.assertIn("MSH", out)
        self.assertIn("ORU^R01", out)
        self.assertIn("OBX|", out)


class TestASTM(unittest.TestCase):
    def test_checksum(self):
        self.assertEqual(len(astm_checksum("H|1|X||Y")), 3)

    def test_frames(self):
        data = sample_astm()
        frames = extract_frames(data)
        self.assertTrue(len(frames) >= 4)
        types = [f.frame_type for f in frames]
        self.assertIn("H", types)
        self.assertIn("P", types)
        self.assertIn("R", types)

    def test_parse_results(self):
        data = sample_astm()
        frames = extract_frames(data)
        parsed = parse_astm_results(frames)
        self.assertEqual(parsed["last_name"], "ROE")
        self.assertEqual(parsed["first_name"], "JOHN")
        self.assertEqual(len(parsed["results"]), 3)

    def test_build_header(self):
        hdr = build_astm_header("SYSMEX", "LIS")
        self.assertTrue(hdr.startswith(b"\x02H|1|"))


class TestMapper(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(normalize_ident("WBC"), "wbc")
        self.assertEqual(normalize_ident("wbc"), "wbc")
        self.assertEqual(normalize_ident("HGB"), "hgb")
        self.assertEqual(normalize_ident("LYMPH%"), "lymph_pct")
        self.assertEqual(normalize_ident("PLT"), "plt")

    def test_unknown(self):
        self.assertFalse(is_known("ZZZ"))
        self.assertTrue(is_known("wbc"))


class TestIngest(unittest.TestCase):
    def test_detect_protocol(self):
        self.assertEqual(detect_protocol(SAMPLE_HL7.encode()), "hl7")
        self.assertEqual(detect_protocol(sample_astm()), "astm")

    def test_parse_hl7_pipeline(self):
        parsed = parse_message(SAMPLE_HL7.encode())
        self.assertEqual(parsed["protocol"], "hl7")
        self.assertEqual(len(parsed["results"]), 8)
        self.assertEqual(parsed["patient"]["last_name"], "JONES")

    def test_parse_astm_pipeline(self):
        parsed = parse_message(sample_astm())
        self.assertEqual(parsed["protocol"], "astm")
        self.assertEqual(len(parsed["results"]), 3)

    def test_results_payload(self):
        parsed = parse_message(SAMPLE_HL7.encode())
        payload = results_payload_from_parsed(parsed)
        by_key = {r["parameter_name"]: r for r in payload}
        self.assertIn("wbc", by_key)
        self.assertEqual(by_key["wbc"]["flag"], "H")
        self.assertEqual(by_key["hgb"]["flag"], "L")
        self.assertEqual(by_key["plt"]["flag"], "normal")


if __name__ == "__main__":
    unittest.main(verbosity=2)