from __future__ import annotations

import sys
import time
import math
import threading
import numpy as np

import cv2

from .calibration import CalibrationBuffer
from .config import CombineConfig
from .models import AttentionState, SystemState, SystemEvent
from .pose import VisionEstimator
from .state_machine import SystemStateMachine
from . import event_bus, ws_server, db as _db
from .api_handler import handle_status, handle_history, set_cors_headers


class AppState:
    trigger_start = False
    trigger_end = False


class WebStreamer:
    frame_bytes = b''
    _cond = threading.Condition()

    class Handler(__import__('http.server').server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html = """<!DOCTYPE html>
<html>
<head>
    <title>AIOT Monitor</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { background: #111; color: #fff; font-family: sans-serif; text-align: center; }
        img { max-width: 100%; border: 2px solid #444; border-radius: 8px; }
        .btn { color: white; padding: 15px 30px; font-size: 18px; border: none; border-radius: 5px;
               cursor: pointer; font-weight: bold; display: inline-block; margin: 10px; text-decoration: none; }
        .btn-start { background: #2ed573; }
        .btn-end   { background: #ff4757; }
    </style>
</head>
<body>
    <h2>AIOT Monitor Stream</h2>
    <div><img src="/stream.mjpg"/></div>
    <div>
        <a class="btn btn-start" href="/start">Start</a>
        <a class="btn btn-end"   href="/end">End</a>
    </div>
</body>
</html>"""
                self.wfile.write(html.encode('utf-8'))

            elif self.path == '/stream.mjpg':
                self.send_response(200)
                self.send_header('Age', '0')
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
                self.end_headers()
                try:
                    while True:
                        with WebStreamer._cond:
                            WebStreamer._cond.wait(timeout=2.0)
                            fb = WebStreamer.frame_bytes
                        if fb:
                            self.wfile.write(
                                b'--FRAME\r\n'
                                b'Content-Type: image/jpeg\r\n'
                                + f'Content-Length: {len(fb)}\r\n\r\n'.encode()
                                + fb
                                + b'\r\n'
                            )
                            self.wfile.flush()
                except Exception:
                    pass

            elif self.path == '/start':
                AppState.trigger_start = True
                print("Received /start command")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                set_cors_headers(self)
                self.end_headers()
                self.wfile.write(b'OK: start')

            elif self.path == '/end':
                AppState.trigger_end = True
                print("Received /end command")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                set_cors_headers(self)
                self.end_headers()
                self.wfile.write(b'OK: end')

            elif self.path == '/api/status':
                handle_status(self)

            elif self.path.startswith('/api/history'):
                handle_history(self, self.path)

            else:
                self.send_error(404)

        def do_OPTIONS(self):
            self.send_response(204)
            set_cors_headers(self)
            self.end_headers()

        def do_POST(self):
            self.send_error(405)

        def log_message(self, format, *args):
            pass

    @staticmethod
    def start(port: int = 9547) -> None:
        from http.server import ThreadingHTTPServer
        server = ThreadingHTTPServer(('0.0.0.0', port), WebStreamer.Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"Web streaming started on http://0.0.0.0:{port}")

    @staticmethod
    def update_frame(frame) -> None:
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            with WebStreamer._cond:
                WebStreamer.frame_bytes = jpeg.tobytes()
                WebStreamer._cond.notify_all()


class RPiStreamCamera:
    """CSI camera fallback via rpicam-vid subprocess (no Picamera2 / simplejpeg dependency)."""

    def __init__(self, w: int, h: int):
        import subprocess
        import shutil
        cmd_name = "rpicam-vid" if shutil.which("rpicam-vid") else "libcamera-vid"
        cmd = [
            cmd_name, "-t", "0", "--codec", "mjpeg",
            "--width", str(w), "--height", str(h), "--framerate", "30",
            "--inline", "--nopreview", "-o", "-"
        ]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self.buffer = b''

    def read(self):
        while True:
            chunk = self.proc.stdout.read(4096)
            if not chunk:
                return False, None
            self.buffer += chunk
            a = self.buffer.find(b'\xff\xd8')
            b = self.buffer.find(b'\xff\xd9')
            if a != -1 and b != -1:
                jpg = self.buffer[a:b + 2]
                self.buffer = self.buffer[b + 2:]
                frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                if frame is not None:
                    return True, frame

    def isOpened(self):
        return self.proc.poll() is None

    def release(self):
        self.proc.terminate()


def main() -> int:
    config = CombineConfig()
    return run(config)


def run(config: CombineConfig) -> int:
    # Pi 版：完全不使用 Picamera2（避免 simplejpeg numpy ABI 衝突）
    # 優先嘗試 cv2.VideoCapture（USB 鏡頭），失敗才 fallback 到 RPiStreamCamera（CSI 鏡頭）
    cap = cv2.VideoCapture(config.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)

    if not cap.isOpened():
        cap.release()
        print("OpenCV VideoCapture failed, trying RPiStreamCamera (CSI) fallback...")
        cap = RPiStreamCamera(config.frame_width, config.frame_height)
        if not cap.isOpened():
            print("ERROR: Cannot open any camera", file=sys.stderr)
            return 1
        print("Using RPiStreamCamera (CSI via rpicam-vid)")
    else:
        print(f"Using OpenCV VideoCapture (camera index {config.camera_index})")

    estimator = VisionEstimator(config)
    calibration = CalibrationBuffer(config)

    WebStreamer.start(config.web_port)
    ws_server.start('0.0.0.0', config.ws_port)
    _db.start(config.db_path)

    state_machine = None
    system_state = SystemState.IDLE
    calib_start_time = 0.0
    _last_idle_publish = 0.0
    _last_calib_print = -1

    try:
        while True:
            loop_start = time.time()

            ok, frame = cap.read()

            if not ok:
                print("Camera frame read failed", file=sys.stderr)
                break

            frame = cv2.flip(frame, 1)

            head_pose, eye_state, face_lm, pose_lm = estimator.estimate(frame)

            if eye_state and eye_state.irises:
                for (cx, cy, r) in eye_state.irises:
                    cv2.circle(frame, (cx, cy), r + 2, (0, 255, 255), 1, cv2.LINE_AA)
                    cv2.circle(frame, (cx, cy), 1, (0, 255, 255), -1, cv2.LINE_AA)

            if AppState.trigger_end:
                system_state = SystemState.IDLE
                state_machine = None
                _last_idle_publish = 0.0
                print("System stopped via /end -> back to IDLE.")
                AppState.trigger_end = False
                AppState.trigger_start = False

            if AppState.trigger_start:
                if system_state == SystemState.IDLE:
                    system_state = SystemState.CALIBRATING
                    calib_start_time = time.time()
                    calibration = CalibrationBuffer(config)
                    _last_calib_print = -1
                    print("System started via /start -> auto calibrating...")
                AppState.trigger_start = False

            if system_state == SystemState.IDLE:
                cv2.putText(frame, "Waiting for /start ...", (30, 80),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                now = time.time()
                if now - _last_idle_publish >= 1.0:
                    _last_idle_publish = now
                    event_bus.publish(SystemEvent(
                        timestamp=now,
                        system_state=SystemState.IDLE,
                    ))

            elif system_state == SystemState.CALIBRATING:
                elapsed = time.time() - calib_start_time
                remaining = max(0, config.calibration_seconds - elapsed)
                remaining_int = int(remaining)

                cv2.putText(frame, f"Calibrating... {remaining_int}s",
                            (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

                if remaining_int != _last_calib_print:
                    print(f"[CALIB] {remaining_int}s remaining")
                    _last_calib_print = remaining_int

                if elapsed < config.calibration_seconds:
                    if head_pose:
                        calibration.add_face(head_pose, eye_state)
                    if pose_lm:
                        try:
                            L_ear = [pose_lm.landmark[7].x, pose_lm.landmark[7].y, pose_lm.landmark[7].z]
                            R_ear = [pose_lm.landmark[8].x, pose_lm.landmark[8].y, pose_lm.landmark[8].z]
                            L_shoulder = [pose_lm.landmark[11].x, pose_lm.landmark[11].y, pose_lm.landmark[11].z]
                            R_shoulder = [pose_lm.landmark[12].x, pose_lm.landmark[12].y, pose_lm.landmark[12].z]
                            P_ear = np.array([(L_ear[0] + R_ear[0]) / 2,
                                              (L_ear[1] + R_ear[1]) / 2,
                                              (L_ear[2] + R_ear[2]) / 2])
                            P_shoulder = np.array([(L_shoulder[0] + R_shoulder[0]) / 2,
                                                   (L_shoulder[1] + R_shoulder[1]) / 2,
                                                   (L_shoulder[2] + R_shoulder[2]) / 2])
                            V_neck = P_ear - P_shoulder
                            d_neck = math.sqrt((P_ear[0] - P_shoulder[0]) ** 2 + (P_ear[1] - P_shoulder[1]) ** 2)
                            d_ear = math.sqrt((L_ear[0] - R_ear[0]) ** 2 + (L_ear[1] - R_ear[1]) ** 2)
                            calibration.add_posture(
                                V_neck, P_shoulder[1], d_ear, d_neck,
                                L_shoulder[1] - R_shoulder[1], L_ear[1] - R_ear[1]
                            )
                        except Exception:
                            pass

                    event_bus.publish(SystemEvent(
                        timestamp=time.time(),
                        system_state=SystemState.CALIBRATING,
                        seconds_outside_zone=remaining,
                    ))
                else:
                    zones = calibration.build_zones()
                    posture_baseline = calibration.build_posture_baseline()
                    state_machine = SystemStateMachine(config, zones, posture_baseline)
                    system_state = SystemState.TRACKING
                    print("Calibration complete.")

            elif system_state == SystemState.TRACKING:
                event = state_machine.update(time.time(), head_pose, eye_state, face_lm, pose_lm)
                event_bus.publish(event)
                _draw_overlay(frame, event, state_machine.zones, config)

                if not hasattr(run, '_last_debug') or time.time() - run._last_debug >= 1.0:
                    run._last_debug = time.time()
                    focus_str = f"Focus: {event.attention_state.value}"
                    ratio_str = f"DistractRate: {event.distraction_ratio:.0%}"
                    posture_str = "Posture: OK"
                    if event.posture_metrics:
                        pm = event.posture_metrics
                        if pm.is_bad_posture:
                            posture_str = f"Posture: BAD ({', '.join(pm.bad_posture_reasons)})"
                        posture_str += f" | PostureRate: {pm.posture_ratio:.0%}"
                    print(f"[TRACK] {focus_str} | {ratio_str} | {posture_str}")

            elapsed = time.time() - loop_start
            sleep_time = max(0.0, (1.0 / config.fps_limit) - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

            WebStreamer.update_frame(frame)

    finally:
        estimator.close()
        cap.release()

    return 0


def _draw_overlay(frame, event: SystemEvent, zones, config: CombineConfig) -> None:
    color_map = {
        AttentionState.FOCUSED: (60, 220, 80),
        AttentionState.PENDING_DISTRACTION: (0, 200, 255),
        AttentionState.NO_FACE: (0, 200, 255),
        AttentionState.DISTRACTED: (40, 40, 255),
        AttentionState.FATIGUED: (255, 0, 255),
    }

    att_color = color_map.get(event.attention_state, (255, 255, 255))
    cv2.putText(frame, f"Focus: {event.attention_state.value}",
                (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, att_color, 2, cv2.LINE_AA)

    if event.head_pose:
        cv2.putText(frame, f"P {event.head_pose.pitch:0.1f} Y {event.head_pose.yaw:0.1f}",
                    (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, att_color, 1)

    if event.eye_state:
        cv2.putText(frame, f"EAR: {event.eye_state.ear:0.2f}",
                    (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, att_color, 1)

        tracker_size = 80
        tx, ty = 20, 110
        cv2.rectangle(frame, (tx, ty), (tx + tracker_size, ty + tracker_size), (40, 40, 40), -1)
        for zone in zones:
            zx1 = max(tx, min(tx + tracker_size, tx + int(zone.gaze_x_min * tracker_size)))
            zx2 = max(tx, min(tx + tracker_size, tx + int(zone.gaze_x_max * tracker_size)))
            zy1 = max(ty, min(ty + tracker_size, ty + int(zone.gaze_y_min * tracker_size)))
            zy2 = max(ty, min(ty + tracker_size, ty + int(zone.gaze_y_max * tracker_size)))
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (100, 255, 100), 1)

        gx = max(tx, min(tx + tracker_size, tx + int(event.eye_state.gaze_x * tracker_size)))
        gy = max(ty, min(ty + tracker_size, ty + int(event.eye_state.gaze_y * tracker_size)))
        dot_color = (0, 0, 255) if event.attention_state in (
            AttentionState.PENDING_DISTRACTION, AttentionState.DISTRACTED) else (0, 255, 0)
        cv2.circle(frame, (gx, gy), 4, dot_color, -1)

        ratio = event.distraction_ratio
        bar_w, bar_h = 150, 10
        bar_x, bar_y = 20, ty + tracker_size + 25
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
        fill_w = int(bar_w * min(1.0, ratio / 0.5))
        fill_color = (0, 255, 0) if ratio <= 0.25 else ((0, 200, 255) if ratio <= 0.4 else (0, 0, 255))
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), fill_color, -1)
        cv2.putText(frame, f"Distraction: {ratio * 100:0.1f}% (Q:{event.queue_size})",
                    (bar_x, bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    p_x = frame.shape[1] - 250
    if event.posture_metrics:
        m = event.posture_metrics
        p_color = (0, 0, 255) if m.is_bad_posture else (0, 255, 0)
        cv2.putText(frame, "Bad Posture!" if m.is_bad_posture else "Posture: OK",
                    (p_x, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, p_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Neck Ang: {m.v_neck_angle:0.1f}", (p_x, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Shld Drp: {m.shoulder_drop:0.3f}", (p_x, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Lat Tilt: {m.lateral_diff:0.3f}", (p_x, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Prox: {m.ear_ratio:0.2f}x", (p_x, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        p_ratio = m.posture_ratio
        p_bar_w, p_bar_h = 150, 10
        p_bar_x, p_bar_y = p_x, 145
        cv2.rectangle(frame, (p_bar_x, p_bar_y), (p_bar_x + p_bar_w, p_bar_y + p_bar_h), (40, 40, 40), -1)
        p_fill_w = int(p_bar_w * min(1.0, p_ratio / 0.5))
        p_fill_color = (0, 255, 0) if p_ratio <= 0.25 else ((0, 200, 255) if p_ratio <= 0.4 else (0, 0, 255))
        cv2.rectangle(frame, (p_bar_x, p_bar_y), (p_bar_x + p_fill_w, p_bar_y + p_bar_h), p_fill_color, -1)
        cv2.putText(frame, f"Posture Rate: {p_ratio * 100:0.1f}% (Q:{m.posture_queue_size})",
                    (p_bar_x, p_bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        if m.is_bad_posture:
            y_off = p_bar_y + 25
            for r in m.bad_posture_reasons:
                cv2.putText(frame, f"- {r}", (p_x, y_off), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                y_off += 20
    else:
        cv2.putText(frame, "Posture: No Data", (p_x, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)


if __name__ == '__main__':
    sys.exit(main())
