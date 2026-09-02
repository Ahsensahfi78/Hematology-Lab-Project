"""Simulate a haematology analyzer pushing messages to the listener.

Usage:
    python simulate_device.py hl7    # send HL7 ORU^R01 via MLLP
    python simulate_device.py astm   # send ASTM E1394 frames via raw TCP
"""

import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.sample_messages import SAMPLE_HL7, sample_astm

HOST = "127.0.0.1"
PORT = 5000

MLLP_START = b"\x0b"
MLLP_END = b"\x1c\x0d"


def send_mllp(message: str) -> str:
    """Wrap an HL7 message in MLLP framing and send over TCP."""
    payload = MLLP_START + message.encode("latin-1") + MLLP_END
    with socket.create_connection((HOST, PORT), timeout=10) as s:
        s.sendall(payload)
        ack = s.recv(1)
        return "ACK (0x06)" if ack == b"\x06" else f"response byte: {ack.hex()}"


def send_raw_astm(data: bytes) -> str:
    """Send pre-framed ASTM bytes over a raw TCP connection."""
    with socket.create_connection((HOST, PORT), timeout=10) as s:
        s.sendall(data)
        ack = s.recv(1)
        return "ACK (0x06)" if ack == b"\x06" else f"response byte: {ack.hex()}"


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "hl7"
    if mode == "hl7":
        print("Sending HL7 message via MLLP…")
        for i in range(2):
            print("  ->", send_mllp(SAMPLE_HL7))
            time.sleep(0.5)
    elif mode == "astm":
        print("Sending ASTM E1394 frames…")
        print("  ->", send_raw_astm(sample_astm()))
    else:
        print("Usage: simulate_device.py [hl7|astm]")