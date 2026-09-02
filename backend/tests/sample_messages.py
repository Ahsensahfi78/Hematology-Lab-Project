"""Sample HL7 v2.4 and ASTM E1394 messages for testing / simulation."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


SAMPLE_HL7 = (
    "MSH|^~\\&|SYSMEX|LAB|LIS|HOSP|20260902103000|"
    "ORU^R01|MSG001|P|2.4|\r"
    "PID|1|PT90001|90001^^^HOSP||JONES^MARY^||19781010|F\r"
    "OBR|1|SP90001||CBC000001^CBC PLATELET|||20260902103000|||||"
    "DR^SMITH^JOHN^^^^^^|\r"
    "OBX|1|NM|WBC^White Blood Cell||12.4|x10^3/uL|4.0-11.0|H|||F\r"
    "OBX|2|NM|RBC^Red Blood Cell||4.1|M/uL|4.0-5.2|N|||F\r"
    "OBX|3|NM|HGB^Haemoglobin||11.8|g/dL|12.0-16.0|L|||F\r"
    "OBX|4|NM|HCT^Haematocrit||36.5|%|36.0-48.0|N|||F\r"
    "OBX|5|NM|MCV^Mean Corpuscular Volume||89.0|fL|80.0-100.0|N|||F\r"
    "OBX|6|NM|PLT^Platelet||180|10^9/L|150-450|N|||F\r"
    "OBX|7|NM|LYMPH%^Lymphocytes||28.0|%|20-45|N|||F\r"
    "OBX|8|NM|GRAN%^Granulocytes||60.0|%|45-70|N|||F\r"
)


def sample_astm() -> bytes:
    """Build a compound ASTM E1394 message (H + P + R records)."""
    from app.protocol.astm import (
        STX,
        ETX,
        CR,
        LF,
        astm_checksum,
    )

    def frame(body):
        return f"{STX}{body}{astm_checksum(body)}{ETX}{CR}{LF}".encode("latin-1")

    h = frame("H|1|SYSMEX||LIS|||P|1||E1394-97||")
    p = frame("P|1|LAB01|90002|ROE^JOHN^AFTERNOON||19700101|M|")
    r1 = frame("R|1|WBC^White Blood Cell^CBC|12.0|x10^3/uL|4.0-11.0|H|||")
    r2 = frame("R|2|HGB^Haemoglobin^CBC|14.0|g/dL|13.5-18.0|N|||")
    r3 = frame("R|3|PLT^Platelet^CBC|140|10^9/L|150-450|L|||")
    l = frame("L|1|N")
    return h + p + r1 + r2 + r3 + l


if __name__ == "__main__":
    print("=== HL7 sample ===")
    print(SAMPLE_HL7.replace("\r", "\n"))
    print("=== ASTM bytes ===")
    print(repr(sample_astm()))