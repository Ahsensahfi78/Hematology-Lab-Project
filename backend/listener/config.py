"""Configuration for the device listener service.

Loaded from environment variables or a `listener_config.json` file.
"""

import json
import os

DEFAULTS = {
    "host": "0.0.0.0",
    "port": 5000,
    "api_base": "http://127.0.0.1:8000",
    "api_username": "technician",
    "api_password": "lab123",
    "protocol": "mllp",       # 'mllp' (HL7 over TCP) or 'raw' or 'astm'
    "serial_port": "",
    "serial_baud": 9600,
    "panel": "LMG",
    "log_file": "",
}


def load_config(path: str = None) -> dict:
    cfg = dict(DEFAULTS)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    # env overrides
    for key in DEFAULTS:
        env = os.environ.get(f"LISTENER_{key.upper()}")
        if env is not None:
            cfg[key] = env
    return cfg