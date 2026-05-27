from __future__ import annotations

import json
import sqlite3
import threading
import time
from typing import Optional
from urllib.parse import urlparse, parse_qs

from . import event_bus
from .models import SystemEvent


_DB_PATH: str = "events.db"


def init_db(path: str) -> None:
    con = sqlite3.connect(path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp            REAL    NOT NULL,
            system_state         TEXT,
            attention_state      TEXT,
            matched_zone         TEXT,
            seconds_outside_zone REAL,
            pitch                REAL,
            yaw                  REAL,
            roll                 REAL,
            ear                  REAL,
            gaze_x               REAL,
            gaze_y               REAL,
            is_bad_posture       INTEGER,
            bad_posture_reasons  TEXT,
            distraction_ratio    REAL,
            posture_ratio        REAL,
            queue_size           INTEGER,
            posture_queue_size   INTEGER
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON events(timestamp)")
    con.commit()
    con.close()


def _event_to_row(event: SystemEvent) -> tuple:
    hp = event.head_pose
    es = event.eye_state
    pm = event.posture_metrics
    return (
        event.timestamp,
        event.system_state.value if event.system_state else None,
        event.attention_state.value if event.attention_state else None,
        event.matched_zone,
        event.seconds_outside_zone,
        hp.pitch if hp else None,
        hp.yaw if hp else None,
        hp.roll if hp else None,
        es.ear if es else None,
        es.gaze_x if es else None,
        es.gaze_y if es else None,
        int(pm.is_bad_posture) if pm else None,
        json.dumps(pm.bad_posture_reasons) if pm else None,
        event.distraction_ratio,
        pm.posture_ratio if pm else None,
        event.queue_size,
        pm.posture_queue_size if pm else None,
    )


def _writer_loop(q: "event_bus.queue.Queue", db_path: str) -> None:
    con = sqlite3.connect(db_path)
    insert_sql = """
        INSERT INTO events (
            timestamp, system_state, attention_state, matched_zone,
            seconds_outside_zone, pitch, yaw, roll, ear, gaze_x, gaze_y,
            is_bad_posture, bad_posture_reasons, distraction_ratio,
            posture_ratio, queue_size, posture_queue_size
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """
    batch: list[tuple] = []
    last_commit = time.time()

    while True:
        try:
            event: SystemEvent = q.get(timeout=5.0)
            batch.append(_event_to_row(event))
        except Exception:
            pass

        now = time.time()
        if batch and (len(batch) >= 10 or now - last_commit >= 5.0):
            try:
                con.executemany(insert_sql, batch)
                con.commit()
            except Exception as e:
                print(f"[DB] Write error: {e}")
            batch.clear()
            last_commit = now


def start(db_path: str = "events.db") -> None:
    global _DB_PATH
    _DB_PATH = db_path
    init_db(db_path)
    q = event_bus.subscribe()
    t = threading.Thread(target=_writer_loop, args=(q, db_path), daemon=True)
    t.start()


def query_history(
    db_path: str,
    start_ts: Optional[float] = None,
    end_ts: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    import os
    if not os.path.exists(db_path):
        return []
    try:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.OperationalError:
        return []
    con.row_factory = sqlite3.Row
    conditions = []
    params: list = []
    if start_ts is not None:
        conditions.append("timestamp >= ?")
        params.append(start_ts)
    if end_ts is not None:
        conditions.append("timestamp <= ?")
        params.append(end_ts)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    params += [limit, offset]
    rows = con.execute(
        f"SELECT * FROM events {where} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
        params,
    ).fetchall()
    con.close()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("bad_posture_reasons"):
            try:
                d["bad_posture_reasons"] = json.loads(d["bad_posture_reasons"])
            except Exception:
                pass
        result.append(d)
    return result
