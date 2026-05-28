from __future__ import annotations

import asyncio
import json
import threading
from typing import Optional, Any

from . import event_bus
from .models import SystemEvent, SystemState, AttentionState


_loop: Optional[asyncio.AbstractEventLoop] = None
_async_queues: list[asyncio.Queue] = []
_aq_lock = threading.Lock()
_loop_ready = threading.Event()


def event_to_dict(event: SystemEvent) -> dict:
    hp = event.head_pose
    es = event.eye_state
    pm = event.posture_metrics
    return {
        "timestamp": event.timestamp,
        "system_state": event.system_state.value if event.system_state else None,
        "attention_state": event.attention_state.value if event.attention_state else None,
        "matched_zone": event.matched_zone,
        "seconds_outside_zone": event.seconds_outside_zone,
        "distraction_ratio": event.distraction_ratio,
        "queue_size": event.queue_size,
        "head_pose": {"pitch": hp.pitch, "yaw": hp.yaw, "roll": hp.roll} if hp else None,
        "eye_state": {
            "ear": es.ear,
            "is_blinking": es.is_blinking,
            "gaze_x": es.gaze_x,
            "gaze_y": es.gaze_y,
        } if es else None,
        "posture_metrics": {
            "v_neck_angle": pm.v_neck_angle,
            "shoulder_drop": pm.shoulder_drop,
            "ear_ratio": pm.ear_ratio,
            "neck_ratio": pm.neck_ratio,
            "lateral_diff": pm.lateral_diff,
            "is_bad_posture": pm.is_bad_posture,
            "bad_posture_reasons": pm.bad_posture_reasons,
            "posture_ratio": pm.posture_ratio,
            "posture_queue_size": pm.posture_queue_size,
        } if pm else None,
    }


def publish_from_sync(event: SystemEvent) -> None:
    if _loop is None or not _loop.is_running():
        return
    with _aq_lock:
        queues = list(_async_queues)
    for q in queues:
        _loop.call_soon_threadsafe(q.put_nowait, event)


async def _handler(websocket: Any) -> None:
    q: asyncio.Queue = asyncio.Queue(maxsize=60)
    with _aq_lock:
        _async_queues.append(q)
    try:
        while True:
            event: SystemEvent = await q.get()
            try:
                await websocket.send(json.dumps(event_to_dict(event)))
            except Exception:
                break
    finally:
        with _aq_lock:
            try:
                _async_queues.remove(q)
            except ValueError:
                pass


async def _run_server(host: str, port: int) -> None:
    import websockets
    async with websockets.serve(_handler, host, port, origins=None):
        _loop_ready.set()
        await asyncio.Future()


def _thread_main(host: str, port: int) -> None:
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_until_complete(_run_server(host, port))


def start(host: str = "0.0.0.0", port: int = 9548) -> None:
    t = threading.Thread(target=_thread_main, args=(host, port), daemon=True)
    t.start()

    # Wait for asyncio loop + WebSocket server to be ready before bridging events
    _loop_ready.wait(timeout=10.0)

    sync_q = event_bus.subscribe()

    def _bridge_loop() -> None:
        while True:
            try:
                event = sync_q.get()
                publish_from_sync(event)
            except Exception:
                pass

    bridge = threading.Thread(target=_bridge_loop, daemon=True)
    bridge.start()
    print(f"WebSocket server started on ws://{host}:{port}")
