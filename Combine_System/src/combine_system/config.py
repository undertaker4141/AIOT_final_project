from dataclasses import dataclass
from typing import Optional

@dataclass
class CombineConfig:
    # Camera settings
    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    fps_limit: float = 30.0
    web_port: int = 9547

    # Alert API URLs (指向本地 Node B mock，實體 ESP32 部署時再改回外部 URL)
    alert_distraction_url: str = "http://localhost:9549/notfocus"
    alert_posture_url: str = "http://localhost:9549/badposture"

    # Calibration settings (統一為 10 秒)
    calibration_seconds: float = 10.0

    # Model paths
    face_landmarker_model_path: Optional[str] = "models/face_landmarker.task"
    min_detection_confidence: float = 0.5
    min_tracking_confidence: float = 0.5

    # Focus Zone Generation heuristics
    min_samples_for_two_zones: int = 50
    pitch_margin_degrees: float = 12.0
    yaw_margin_degrees: float = 18.0
    gaze_margin_x: float = 0.15
    gaze_margin_y: float = 0.20

    # Focus State Machine heuristics
    absence_threshold_seconds: float = 8.0
    fatigue_closed_eyes_seconds: float = 2.0
    blink_rate_window_seconds: float = 60.0
    turn_focused_iris_ratio: float = 1.3
    ear_threshold: float = 0.21

    # Long-term focus metrics
    long_term_window_frames: int = 200
    long_term_distraction_threshold: int = 80

    # Posture heuristics
    posture_q_size: int = 15
    posture_alert_threshold_time: float = 3.0
    posture_forward_head_angle: float = 12.0
    posture_slouch_shoulder_drop: float = 0.035
    posture_slouch_neck_ratio: float = 0.85
    posture_too_close_ear_ratio: float = 1.15
    posture_lateral_tilt_diff: float = 0.04

    # Long-term posture metrics
    posture_long_term_window_frames: int = 200
    posture_long_term_distraction_threshold: int = 80

    # WebSocket and persistence
    ws_port: int = 9548
    db_path: str = "events.db"
