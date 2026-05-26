from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional, List, Tuple

class SystemState(enum.Enum):
    IDLE = "idle"
    CALIBRATING = "calibrating"
    TRACKING = "tracking"

class AttentionState(enum.Enum):
    FOCUSED = "focused"
    PENDING_DISTRACTION = "pending_distraction"
    NO_FACE = "no_face"
    DISTRACTED = "distracted"
    FATIGUED = "fatigued"

@dataclass
class HeadPose:
    pitch: float
    yaw: float
    roll: float

@dataclass
class EyeState:
    ear: float
    is_blinking: bool
    gaze_x: float
    gaze_y: float
    irises: Optional[List[Tuple[int, int, int]]] = None
    iris_ratio: float = 1.0

@dataclass
class AttentionZone:
    name: str
    pitch_min: float
    pitch_max: float
    yaw_min: float
    yaw_max: float
    gaze_x_min: float = 0.0
    gaze_x_max: float = 1.0
    gaze_y_min: float = 0.0
    gaze_y_max: float = 1.0

    def contains(self, pose: HeadPose, eye_state: Optional[EyeState] = None) -> bool:
        if not (self.pitch_min <= pose.pitch <= self.pitch_max):
            return False
        if not (self.yaw_min <= pose.yaw <= self.yaw_max):
            return False
        if eye_state is not None:
            if not (self.gaze_x_min <= eye_state.gaze_x <= self.gaze_x_max):
                return False
            if not (self.gaze_y_min <= eye_state.gaze_y <= self.gaze_y_max):
                return False
        return True

@dataclass
class PostureMetrics:
    v_neck_angle: float
    shoulder_drop: float
    ear_ratio: float
    neck_ratio: float
    lateral_diff: float
    is_bad_posture: bool
    bad_posture_reasons: List[str]
    posture_ratio: float = 0.0
    posture_queue_size: int = 0

@dataclass
class SystemEvent:
    timestamp: float
    system_state: SystemState
    attention_state: Optional[AttentionState] = None
    head_pose: Optional[HeadPose] = None
    eye_state: Optional[EyeState] = None
    posture_metrics: Optional[PostureMetrics] = None
    matched_zone: Optional[str] = None
    seconds_outside_zone: float = 0.0
    distraction_ratio: float = 0.0
    queue_size: int = 0
