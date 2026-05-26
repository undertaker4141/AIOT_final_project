from __future__ import annotations

import sys
import time
import math
import numpy as np

import cv2

from .calibration import CalibrationBuffer
from .config import CombineConfig
from .models import AttentionState, SystemState, SystemEvent
from .pose import VisionEstimator
from .state_machine import SystemStateMachine
class AppState:
    trigger_start = False
    trigger_end = False

class WebStreamer:
    import threading
    frame_bytes = b''
    lock = threading.Lock()

    class Handler(__import__('http.server').server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                html = """
                <html>
                <head>
                    <title>MakeNTU Combine System</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { background: #111; color: #fff; font-family: sans-serif; text-align: center; }
                        img { max-width: 100%; border: 2px solid #444; border-radius: 8px; }
                        .btn { color: white; padding: 15px 30px; font-size: 18px; border: none; border-radius: 5px; cursor: pointer; margin-top: 20px; font-weight: bold; display: inline-block; margin: 10px; }
                        .btn-start { background: #2ed573; }
                        .btn-start:hover { background: #7bed9f; }
                        .btn-end { background: #ff4757; }
                        .btn-end:hover { background: #ff6b81; }
                        .btn-calib { background: #1e90ff; }
                        .btn-calib:hover { background: #70a1ff; }
                    </style>
                </head>
                <body>
                    <h2>AIOT Monitor Stream</h2>
                    <div><img src="/stream.mjpg"/></div>
                    <div>
                        <a class="btn btn-start" href="/start">Start</a>
                        <a class="btn btn-end" href="/end">End</a>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(html.encode('utf-8'))
            elif self.path == '/stream.mjpg':
                self.send_response(200)
                self.send_header('Age', 0)
                self.send_header('Cache-Control', 'no-cache, private')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
                self.end_headers()
                try:
                    import time
                    while True:
                        with WebStreamer.lock:
                            fb = WebStreamer.frame_bytes
                        if fb:
                            self.wfile.write(b'--FRAME\r\n')
                            self.send_header('Content-Type', 'image/jpeg')
                            self.send_header('Content-Length', str(len(fb)))
                            self.end_headers()
                            self.wfile.write(fb)
                            self.wfile.write(b'\r\n')
                        time.sleep(0.05)
                except Exception:
                    pass
            elif self.path == '/start':
                AppState.trigger_start = True
                print("Received /start command")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK: start')
            elif self.path == '/end':
                AppState.trigger_end = True
                print("Received /end command")
                self.send_response(200)
                self.send_header('Content-type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'OK: end')
            else:
                self.send_error(404)
        
        def do_POST(self):
            self.send_error(405)

        def log_message(self, format, *args):
            pass

    @staticmethod
    def start(port=9547):
        import threading
        from http.server import HTTPServer
        server = HTTPServer(('0.0.0.0', port), WebStreamer.Handler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"Web streaming started on http://0.0.0.0:{port}")

    @staticmethod
    def update_frame(frame):
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ret:
            with WebStreamer.lock:
                WebStreamer.frame_bytes = jpeg.tobytes()


def main() -> int:
    config = CombineConfig()
    return run(config)


def run(config: CombineConfig) -> int:
    use_picamera = False
    try:
        import os
        import sys
        import subprocess
        import ast
        
        # Query the system Python for its sys.path to get all Debian-specific C-extension paths
        try:
            out = subprocess.check_output(['/usr/bin/python3', '-c', 'import sys; print(repr(sys.path))']).decode('utf-8').strip()
            sys_paths = ast.literal_eval(out)
            for p in sys_paths:
                if p and os.path.exists(p) and p not in sys.path:
                    sys.path.append(p)
        except Exception as ex:
            print(f"Warning: Could not fetch system paths: {ex}", file=sys.stderr)
            
        from picamera2 import Picamera2
        use_picamera = True
    except ImportError as e:
        print(f"Picamera2 import failed (falling back to Subprocess/OpenCV): {e}", file=sys.stderr)
        pass

    class RPiStreamCamera:
        def __init__(self, w, h):
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
            import numpy as np
            while True:
                chunk = self.proc.stdout.read(4096)
                if not chunk:
                    return False, None
                self.buffer += chunk
                a = self.buffer.find(b'\xff\xd8')
                b = self.buffer.find(b'\xff\xd9')
                if a != -1 and b != -1:
                    jpg = self.buffer[a:b+2]
                    self.buffer = self.buffer[b+2:]
                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        return True, frame

        def release(self):
            self.proc.terminate()

    if use_picamera:
        print("Using Picamera2 for video capture...")
        picam2 = Picamera2()
        cam_config = picam2.create_video_configuration(main={"size": (config.frame_width, config.frame_height), "format": "bgr888"})
        picam2.configure(cam_config)
        picam2.start()
        cap = None
    else:
        import platform
        if platform.system() == "Linux":
            print("Using RPiStreamCamera (Subprocess fallback)...")
            cap = RPiStreamCamera(config.frame_width, config.frame_height)
        else:
            print("Using OpenCV VideoCapture...")
            cap = cv2.VideoCapture(config.camera_index)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.frame_height)

    estimator = VisionEstimator(config)
    calibration = CalibrationBuffer(config)
    
    WebStreamer.start(config.web_port)
    state_machine = None
    
    system_state = SystemState.IDLE
    calib_start_time = 0

    try:
        while True:
            start_time = time.time()
            
            if use_picamera:
                try:
                    frame = picam2.capture_array()
                    ok = True
                except Exception as e:
                    print(f"Camera frame read failed: {e}", file=sys.stderr)
                    ok = False
            else:
                ok, frame = cap.read()
                
            if not ok:
                print("Camera frame read failed", file=sys.stderr)
                break
                
            frame = cv2.flip(frame, 1) # Mirror

            # Get estimations
            head_pose, eye_state, face_lm, pose_lm = estimator.estimate(frame)

            # Draw basic facial landmarks
            if eye_state and eye_state.irises:
                for (cx, cy, r) in eye_state.irises:
                    cv2.circle(frame, (cx, cy), r + 2, (0, 255, 255), 1, cv2.LINE_AA)
                    cv2.circle(frame, (cx, cy), 1, (0, 255, 255), -1, cv2.LINE_AA)

            # 處理外部 /end 指令：立即重置回 IDLE（優先處理）
            if AppState.trigger_end:
                system_state = SystemState.IDLE
                state_machine = None
                print("System stopped via /end -> back to IDLE.")
                AppState.trigger_end = False
                AppState.trigger_start = False  # 清除可能同時存在的 start

            # 處理外部 /start 指令：自動觸發校準
            if AppState.trigger_start:
                if system_state == SystemState.IDLE:
                    system_state = SystemState.CALIBRATING
                    calib_start_time = time.time()
                    calibration = CalibrationBuffer(config)
                    print("System started via /start -> auto calibrating...")
                AppState.trigger_start = False

            if system_state == SystemState.IDLE:
                cv2.putText(frame, "Waiting for /start ...", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            
            elif system_state == SystemState.CALIBRATING:
                elapsed = time.time() - calib_start_time
                remaining = int(config.calibration_seconds - elapsed)
                if elapsed < config.calibration_seconds:
                    cv2.putText(frame, f"Calibrating... {remaining}s", (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)
                    # 每秒印一次倒數
                    if not hasattr(run, '_last_calib_print') or run._last_calib_print != remaining:
                        print(f"[CALIB] Calibrating... {remaining}s remaining")
                        run._last_calib_print = remaining
                    
                    if head_pose:
                        calibration.add_face(head_pose, eye_state)
                    
                    if pose_lm:
                        try:
                            L_ear = [pose_lm.landmark[7].x, pose_lm.landmark[7].y, pose_lm.landmark[7].z]
                            R_ear = [pose_lm.landmark[8].x, pose_lm.landmark[8].y, pose_lm.landmark[8].z]
                            L_shoulder = [pose_lm.landmark[11].x, pose_lm.landmark[11].y, pose_lm.landmark[11].z]
                            R_shoulder = [pose_lm.landmark[12].x, pose_lm.landmark[12].y, pose_lm.landmark[12].z]
                            
                            P_ear = np.array([(L_ear[0]+R_ear[0])/2, (L_ear[1]+R_ear[1])/2, (L_ear[2]+R_ear[2])/2])
                            P_shoulder = np.array([(L_shoulder[0]+R_shoulder[0])/2, (L_shoulder[1]+R_shoulder[1])/2, (L_shoulder[2]+R_shoulder[2])/2])
                            V_neck = P_ear - P_shoulder
                            current_d_neck = math.sqrt((P_ear[0]-P_shoulder[0])**2 + (P_ear[1]-P_shoulder[1])**2)
                            current_d_ear = math.sqrt((L_ear[0]-R_ear[0])**2 + (L_ear[1]-R_ear[1])**2)
                            
                            calibration.add_posture(
                                V_neck, P_shoulder[1], current_d_ear, current_d_neck, 
                                L_shoulder[1]-R_shoulder[1], L_ear[1]-R_ear[1]
                            )
                        except Exception:
                            pass
                else:
                    zones = calibration.build_zones()
                    posture_baseline = calibration.build_posture_baseline()
                    state_machine = SystemStateMachine(config, zones, posture_baseline)
                    system_state = SystemState.TRACKING
                    print("Calibration complete.")

            elif system_state == SystemState.TRACKING:
                event = state_machine.update(time.time(), head_pose, eye_state, face_lm, pose_lm)
                _draw_overlay(frame, event, state_machine.zones, config)
                
                # 終端機 debug 輸出（每秒一次）
                if not hasattr(run, '_last_debug_print') or time.time() - run._last_debug_print >= 1.0:
                    run._last_debug_print = time.time()
                    focus_str = f"Focus: {event.attention_state.value}"
                    ratio_str = f"DistractRate: {event.distraction_ratio:.0%}"
                    posture_str = "Posture: OK"
                    if event.posture_metrics:
                        pm = event.posture_metrics
                        if pm.is_bad_posture:
                            posture_str = f"Posture: BAD ({', '.join(pm.bad_posture_reasons)})"
                        posture_str += f" | PostureRate: {pm.posture_ratio:.0%}"
                    print(f"[TRACK] {focus_str} | {ratio_str} | {posture_str}")

            # Enforce FPS Limit
            process_time = time.time() - start_time
            sleep_time = max(0, (1.0 / config.fps_limit) - process_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

            WebStreamer.update_frame(frame)

                
    finally:
        estimator.close()
        if use_picamera:
            picam2.stop()
            picam2.close()
        else:
            cap.release()
        # cv2.destroyAllWindows()

    return 0

def _draw_overlay(frame, event: SystemEvent, zones, config: CombineConfig) -> None:
    # Colors
    color_map = {
        AttentionState.FOCUSED: (60, 220, 80),
        AttentionState.PENDING_DISTRACTION: (0, 200, 255),
        AttentionState.NO_FACE: (0, 200, 255),
        AttentionState.DISTRACTED: (40, 40, 255),
        AttentionState.FATIGUED: (255, 0, 255),
    }
    
    # 1. Left side: Face / Focus
    att_color = color_map.get(event.attention_state, (255, 255, 255))
    cv2.putText(frame, f"Focus: {event.attention_state.value}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, att_color, 2, cv2.LINE_AA)
    
    if event.head_pose:
        cv2.putText(frame, f"P {event.head_pose.pitch:0.1f} Y {event.head_pose.yaw:0.1f}", (20, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.6, att_color, 1)
        
    if event.eye_state:
        cv2.putText(frame, f"EAR: {event.eye_state.ear:0.2f}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.6, att_color, 1)
        
        # Gaze visualizer
        height, width = frame.shape[:2]
        tracker_size = 80
        tx = 20
        ty = 110
        cv2.rectangle(frame, (tx, ty), (tx + tracker_size, ty + tracker_size), (40, 40, 40), -1)
        for zone in zones:
            zx1 = tx + int(zone.gaze_x_min * tracker_size)
            zx2 = tx + int(zone.gaze_x_max * tracker_size)
            zy1 = ty + int(zone.gaze_y_min * tracker_size)
            zy2 = ty + int(zone.gaze_y_max * tracker_size)
            zx1, zx2 = max(tx, min(tx + tracker_size, zx1)), max(tx, min(tx + tracker_size, zx2))
            zy1, zy2 = max(ty, min(ty + tracker_size, zy1)), max(ty, min(ty + tracker_size, zy2))
            cv2.rectangle(frame, (zx1, zy1), (zx2, zy2), (100, 255, 100), 1)
            
        gx = tx + int(event.eye_state.gaze_x * tracker_size)
        gy = ty + int(event.eye_state.gaze_y * tracker_size)
        gx, gy = max(tx, min(tx + tracker_size, gx)), max(ty, min(ty + tracker_size, gy))
        dot_color = (0, 0, 255) if event.attention_state in (AttentionState.PENDING_DISTRACTION, AttentionState.DISTRACTED) else (0, 255, 0)
        cv2.circle(frame, (gx, gy), 4, dot_color, -1)

        # Draw long-term distraction warning bar
        ratio = getattr(event, 'distraction_ratio', 0.0)
        bar_w = 150
        bar_h = 10
        bar_x = 20
        bar_y = ty + tracker_size + 25
        
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (40, 40, 40), -1)
        fill_w = int(bar_w * min(1.0, ratio / 0.5)) # Max out bar when reaching threshold (approx 0.5)
        
        fill_color = (0, 255, 0)
        if ratio > 0.25:
            fill_color = (0, 200, 255)
        if ratio > 0.4:
            fill_color = (0, 0, 255)
            
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + bar_h), fill_color, -1)
        queue_size = getattr(event, 'queue_size', 0)
        cv2.putText(frame, f"Distraction: {ratio*100:0.1f}% (Q:{queue_size})", (bar_x, bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

    # 2. Right side: Posture
    p_x = frame.shape[1] - 250
    if event.posture_metrics:
        m = event.posture_metrics
        p_color = (0, 0, 255) if m.is_bad_posture else (0, 255, 0)
        p_text = "Bad Posture!" if m.is_bad_posture else "Posture: OK"
        cv2.putText(frame, p_text, (p_x, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, p_color, 2, cv2.LINE_AA)
        cv2.putText(frame, f"Neck Ang: {m.v_neck_angle:0.1f}", (p_x, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Shld Drp: {m.shoulder_drop:0.3f}", (p_x, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Lat Tilt: {m.lateral_diff:0.3f}", (p_x, 105), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        cv2.putText(frame, f"Prox: {m.ear_ratio:0.2f}x", (p_x, 125), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Draw long-term posture warning bar
        p_ratio = m.posture_ratio
        p_bar_w = 150
        p_bar_h = 10
        p_bar_x = p_x
        p_bar_y = 145
        
        cv2.rectangle(frame, (p_bar_x, p_bar_y), (p_bar_x + p_bar_w, p_bar_y + p_bar_h), (40, 40, 40), -1)
        p_fill_w = int(p_bar_w * min(1.0, p_ratio / 0.5)) # Max out bar when reaching threshold (approx 0.5)
        
        p_fill_color = (0, 255, 0)
        if p_ratio > 0.25:
            p_fill_color = (0, 200, 255)
        if p_ratio > 0.4:
            p_fill_color = (0, 0, 255)
            
        cv2.rectangle(frame, (p_bar_x, p_bar_y), (p_bar_x + p_fill_w, p_bar_y + p_bar_h), p_fill_color, -1)
        cv2.putText(frame, f"Posture Rate: {p_ratio*100:0.1f}% (Q:{m.posture_queue_size})", (p_bar_x, p_bar_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        
        if m.is_bad_posture:
            y_offset = p_bar_y + 25
            for r in m.bad_posture_reasons:
                cv2.putText(frame, f"- {r}", (p_x, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
                y_offset += 20
    else:
        cv2.putText(frame, "Posture: No Data", (p_x, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 255), 1)

if __name__ == "__main__":
    sys.exit(main())
