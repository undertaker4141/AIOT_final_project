from __future__ import annotations

import json
import threading
from typing import Optional
from urllib.parse import urlparse, parse_qs

from . import event_bus, db as _db
from .models import SystemEvent
from .ws_server import event_to_dict

_lock = threading.Lock()
_latest_event: Optional[SystemEvent] = None


def _track_latest(event: SystemEvent) -> None:
    global _latest_event
    with _lock:
        _latest_event = event


def _start_tracker() -> None:
    q = event_bus.subscribe()

    def _loop() -> None:
        while True:
            try:
                event = q.get()
                _track_latest(event)
            except Exception:
                pass

    threading.Thread(target=_loop, daemon=True).start()


_start_tracker()


def set_cors_headers(handler) -> None:
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")


def handle_status(handler) -> None:
    with _lock:
        event = _latest_event
    payload = json.dumps(event_to_dict(event) if event else {}).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    set_cors_headers(handler)
    handler.end_headers()
    handler.wfile.write(payload)


def handle_history(handler, path: str) -> None:
    parsed = urlparse(path)
    qs = parse_qs(parsed.query)

    def _float(key: str) -> Optional[float]:
        v = qs.get(key, [None])[0]
        return float(v) if v is not None else None

    def _int(key: str, default: int) -> int:
        v = qs.get(key, [None])[0]
        return int(v) if v is not None else default

    rows = _db.query_history(
        _db._DB_PATH,
        start_ts=_float("start"),
        end_ts=_float("end"),
        limit=_int("limit", 100),
        offset=_int("offset", 0),
    )
    payload = json.dumps(rows).encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    set_cors_headers(handler)
    handler.end_headers()
    handler.wfile.write(payload)
