"""Background device listener service.

Connects to haematology analyzers over TCP (MLLP or raw/ASTM framing) or an
RS-232 serial port, parses incoming HL7/ASTM messages, and ingests them into
the FastAPI backend.

Handles persistent listening, per-connection read loops, timeouts, and
reconnect logic for the serial/ethernet source.
"""

import logging
import os
import socket
import sys
import threading
import time
from pathlib import Path

# Make the `app` package importable when run as a standalone script.
ROOT = Path(__file__).resolve().parent.parent  # backend/
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.protocol.ingest import APIClient, parse_message, ingest_parsed

# MLLP framing characters
MLLP_START = b"\x0b"
MLLP_END = b"\x1c\x0d"

# Timeouts
CONN_TIMEOUT = 60.0
REBUILD_DELAY = 3.0


def build_logger(config):
    logger = logging.getLogger("device-listener")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    log_file = config.get("log_file")
    if log_file:
        try:
            fh = logging.FileHandler(log_file, encoding="utf-8")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        except Exception:
            pass
    return logger


def extract_mllp_frames(buffer: bytes):
    """Split a raw byte buffer into complete MLLP frames."""
    frames = []
    start = 0
    while True:
        si = buffer.find(MLLP_START, start)
        if si < 0:
            break
        ei = buffer.find(MLLP_END, si)
        if ei < 0:
            break
        frame = buffer[si + 1 : ei]
        frames.append(frame)
        start = ei + len(MLLP_END)
    # return the list of complete frames (caller keeps leftover buffer)
    leftover = buffer[start:]
    return frames, leftover


def _looks_like_astm(buffer: bytes) -> bool:
    """Heuristic: ASTM frames are STX-delimited; MLLP frames start with VT."""
    return buffer[:1] == b"\x02" or (b"\x02" in buffer[:2] and b"\x1c\x0d" not in buffer[:4])


def extract_astm_frames(buffer: bytes):
    """Split a raw byte buffer into complete ASTM frames (STX..ETX+CRLF)."""
    from app.protocol.astm import STX, ETX

    frames = []
    start = 0
    stx_b = STX.encode("latin-1")
    etx_b = ETX.encode("latin-1")
    while True:
        si = buffer.find(stx_b, start)
        if si < 0:
            break
        ei = buffer.find(etx_b, si)
        if ei < 0:
            break
        ei += 1
        # include trailing CR/LF if present
        for extra in (1, 2):
            if ei + extra <= len(buffer) and buffer[ei : ei + extra] in (b"\x0d", b"\x0a", b"\x0d\x0a"):
                ei += extra
                break
        frames.append(buffer[si : ei])
        start = ei
    leftover = buffer[start:]
    return frames, leftover


def process_raw(client: APIClient, raw: bytes, panel: str, logger) -> str:
    """Parse + ingest a raw message, returning a short status string."""
    if not raw or not raw.strip():
        return "empty"
    try:
        parsed = parse_message(raw)
        result = ingest_parsed(client, parsed, panel=panel)
        if "error" in (result or {}):
            logger.error("Ingest failed: %s", result.get("error"))
            return f"error:{result.get('error')}"
        sample = result.get("sample_id", "?")
        status = result.get("verification_status", "?")
        logger.info("Ingested sample %s (%s) from %s", sample, status, parsed.get("protocol"))
        return f"ok:{sample}"
    except Exception as e:
        logger.exception("Error processing message")
        return f"error:{e}"


class TCPListener:
    """TCP socket listener accepting MLLP or raw/ASTM framed HL7 messages."""

    def __init__(self, config, client: APIClient, logger):
        self.config = config
        self.client = client
        self.logger = logger
        self.protocol = config.get("protocol", "mllp")
        self.host = config.get("host", "0.0.0.0")
        self.port = int(config.get("port", 5000))
        self.running = True
        self.sock = None
        self.threads = []

    def start(self):
        self.logger.info(
            "Starting TCP listener on %s:%s protocol=%s",
            self.host, self.port, self.protocol,
        )
        while self.running:
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.sock.bind((self.host, self.port))
                self.sock.listen(5)
                self.sock.settimeout(1.0)
                self.logger.info("TCP listener bound. Waiting for connections…")
                while self.running:
                    try:
                        conn, addr = self.sock.accept()
                    except socket.timeout:
                        continue
                    self.logger.info("Connection from %s", addr)
                    t = threading.Thread(
                        target=self._handle_conn, args=(conn, addr), daemon=True
                    )
                    t.start()
                    self.threads.append(t)
            except Exception as e:
                self.logger.error("Listener error: %s", e)
                if not self.running:
                    break
                time.sleep(REBUILD_DELAY)
            finally:
                if self.sock:
                    try:
                        self.sock.close()
                    except Exception:
                        pass

    def _handle_conn(self, conn, addr):
        conn.settimeout(CONN_TIMEOUT)
        buffer = b""
        is_astm = self.protocol == "astm"
        # ASTM frames arrive as H + P + multiple R + L terminator.
        # Accumulate them until the logical terminator (L) before ingesting.
        astm_batch = b""
        try:
            while self.running:
                # read a chunk
                data = conn.recv(4096)
                if not data:
                    # flush any remaining complete batch before closing
                    if astm_batch:
                        status = process_raw(self.client, astm_batch, self.config.get("panel", "LMG"), self.logger)
                        self._reply(conn, status)
                    break  # closed
                buffer += data
                if not is_astm and _looks_like_astm(buffer):
                    is_astm = True
                frames, buffer = self._split(buffer)

                for frame in frames:
                    if self._is_wakeup(frame):
                        continue
                    if is_astm:
                        # accumulate into a logical ASTM batch
                        astm_batch += frame
                        if self._astm_terminated(frame):
                            status = process_raw(self.client, astm_batch, self.config.get("panel", "LMG"), self.logger)
                            self._reply(conn, status)
                            astm_batch = b""
                    else:
                        status = process_raw(self.client, frame, self.config.get("panel", "LMG"), self.logger)
                        self._reply(conn, status)
        except socket.timeout:
            self.logger.warning("Connection timeout from %s", addr)
        except Exception as e:
            self.logger.error("Connection error %s: %s", addr, e)
        finally:
            try:
                conn.close()
            except Exception:
                pass
            self.logger.info("Closed connection from %s", addr)

    @staticmethod
    def _reply(conn, status):
        try:
            if status.startswith("ok"):
                conn.sendall(b"\x06")  # ACK
            else:
                conn.sendall(b"\x15")  # NAK
        except Exception:
            pass

    def _is_astm_session(self):
        # keep for compatibility; detection is now done inline in _handle_conn
        return self.protocol == "astm"

    @staticmethod
    def _astm_terminated(frame: bytes):
        # An ASTM logical message ends with an L (terminator) record whose
        # body starts with "L|". Check inside the frame (after optional STX).
        body = frame.lstrip(b"\x02\x0d\x0a")
        return body[:2] in (b"L|", b"l|")

    def _split(self, buffer: bytes):
        if self.protocol == "astm" or _looks_like_astm(buffer):
            return extract_astm_frames(buffer)
        # default: MLLP / raw with MLLP framing
        return extract_mllp_frames(buffer)

    @staticmethod
    def _is_wakeup(frame: bytes):
        # Ignore single-char wake/ACK ASCII envelopes that aren't real messages
        return len(frame.strip()) <= 3

    def stop(self):
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


class SerialListener:
    """RS-232 serial listener for legacy analyzers (needs pyserial)."""

    def __init__(self, config, client: APIClient, logger):
        self.config = config
        self.client = client
        self.logger = logger
        self.protocol = config.get("protocol", "raw")
        self.port = config.get("serial_port", "")
        self.baud = int(config.get("serial_baud", 9600))
        self.running = True

    def start(self):
        if not self.port:
            self.logger.error("serial_port not configured; serial listener disabled.")
            return
        try:
            import serial  # pyserial
        except ImportError:
            self.logger.error("pyserial not installed. Run: pip install pyserial")
            return

        self.logger.info("Starting serial listener on %s @ %s baud", self.port, self.baud)
        buffer = b""
        while self.running:
            try:
                with serial.Serial(self.port, self.baud, timeout=1.0) as ser:
                    self.logger.info("Opened serial port %s", self.port)
                    while self.running:
                        data = ser.read(4096)
                        if not data:
                            continue
                        buffer += data
                        frames, buffer = (
                            extract_astm_frames(buffer)
                            if self.protocol == "astm"
                            else extract_mllp_frames(buffer)
                        )
                        for frame in frames:
                            status = process_raw(self.client, frame, self.config.get("panel", "LMG"), self.logger)
                            if status.startswith("ok"):
                                ser.write(b"\x06")
                            else:
                                ser.write(b"\x15")
            except Exception as e:
                self.logger.error("Serial error: %s", e)
                if not self.running:
                    break
                self.logger.info("Reconnecting serial in %ss…", REBUILD_DELAY)
                time.sleep(REBUILD_DELAY)

    def stop(self):
        self.running = False


def main():
    config_path = os.environ.get("LISTENER_CONFIG", "")
    import config as listener_config

    config = listener_config.load_config(config_path or None)
    logger = build_logger(config)

    client = APIClient(config.get("api_base", "http://127.0.0.1:8000"))
    if not client.login(config.get("api_username"), config.get("api_password")):
        logger.error("Could not authenticate with backend API. Exiting.")
        sys.exit(1)
    logger.info("Authenticated with backend at %s", config.get("api_base"))

    protocol = config.get("protocol", "mllp")
    use_serial = bool(config.get("serial_port"))
    if use_serial:
        listener = SerialListener(config, client, logger)
    else:
        listener = TCPListener(config, client, logger)

    try:
        listener.start()
    except KeyboardInterrupt:
        logger.info("Stopping listener…")
        listener.stop()
    finally:
        listener.stop()


if __name__ == "__main__":
    main()