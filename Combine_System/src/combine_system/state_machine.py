from __future__ import annotations

import collections
import math
import numpy as np
from typing import Iterable, Optional

from .config import CombineConfig
from .models import AttentionState, AttentionZone, HeadPose, EyeState, PostureMetrics, SystemEvent, SystemState

import requests
import threading
import time as _time

_alert_cooldown: dict[str, float] = {}
_ALERT_COOLDOWN_SECONDS = 30  # 同一個 API 兩分鐘內不重複發送

def _send_alert_async(url: str):
    if not url: return
    now = _time.time()
    last_sent = _alert_cooldown.get(url, 0)
    if now - last_sent < _ALERT_COOLDOWN_SECONDS:
        return  # 冷卻中，跳過
    _alert_cooldown[url] = now
    def task():
        try:
            requests.get(url, timeout=2)
            print(f"Alert successfully sent to {url}")
        except Exception as e:
            print(f"Failed to send alert to {url}: {e}")
    threading.Thread(target=task, daemon=True).start()


class SystemStateMachine:
    def __init__(self, config: CombineConfig, zones: Iterable[AttentionZone], posture_baseline: dict) -> None:
        self.config = config
        self.zones = list(zones)
        self.posture_baseline = posture_baseline
        
        # Face Attention State
        self.attention_state = AttentionState.FOCUSED
        self._outside_since: Optional[float] = None
        self._blink_history: list[float] = []
        self._is_currently_blinking: bool = False
        self._eyes_closed_since: Optional[float] = None
        self._long_term_queue: collections.deque = collections.deque(maxlen=self.config.long_term_window_frames)

        # Body Posture State (Smoothing queues)
        self.q_size = self.config.posture_q_size
        self.q_angle = collections.deque(maxlen=self.q_size)
        self.q_shoulder_drop = collections.deque(maxlen=self.q_size)
        self.q_ear_ratio = collections.deque(maxlen=self.q_size)
        self.q_lateral_diff = collections.deque(maxlen=self.q_size)
        self.q_neck_ratio = collections.deque(maxlen=self.q_size)
        self.bad_posture_start: Optional[float] = None
        self._posture_long_term_queue: collections.deque = collections.deque(maxlen=self.config.posture_long_term_window_frames)

    def update(
        self, 
        timestamp: float, 
        head_pose: Optional[HeadPose], 
        eye_state: Optional[EyeState],
        face_landmarks: Optional[Any],
        pose_landmarks: Optional[Any]
    ) -> SystemEvent:
        
        # 1. Update Attention
        matched_zone = None
        seconds_outside = 0.0
        
        if head_pose is None:
            if self._outside_since is None:
                self._outside_since = timestamp
            seconds_outside = timestamp - self._outside_since
            self.attention_state = AttentionState.NO_FACE
        else:
            if eye_state is not None:
                if eye_state.is_blinking:
                    if not self._is_currently_blinking:
                        self._is_currently_blinking = True
                        if not self._blink_history or timestamp - self._blink_history[-1] > 0.2:
                            self._blink_history.append(timestamp)
                    if self._eyes_closed_since is None:
                        self._eyes_closed_since = timestamp
                    elif timestamp - self._eyes_closed_since > self.config.fatigue_closed_eyes_seconds:
                        self.attention_state = AttentionState.FATIGUED
                else:
                    self._is_currently_blinking = False
                    self._eyes_closed_since = None

                window_start = timestamp - self.config.blink_rate_window_seconds
                self._blink_history = [t for t in self._blink_history if t >= window_start]

            if self.attention_state != AttentionState.FATIGUED:
                matched_zone_obj = self._matched_zone(head_pose, eye_state)
                if matched_zone_obj is not None:
                    self._outside_since = None
                    self.attention_state = AttentionState.FOCUSED
                    matched_zone = matched_zone_obj.name
                else:
                    if self._outside_since is None:
                        self._outside_since = timestamp
                    seconds_outside = timestamp - self._outside_since
                    self.attention_state = AttentionState.DISTRACTED if seconds_outside >= self.config.absence_threshold_seconds else AttentionState.PENDING_DISTRACTION

        is_distracted = 1 if self.attention_state in (AttentionState.DISTRACTED, AttentionState.PENDING_DISTRACTION, AttentionState.NO_FACE) else 0
        self._long_term_queue.append(is_distracted)
        
        distraction_count = sum(self._long_term_queue)
        if distraction_count >= self.config.long_term_distraction_threshold:
            if getattr(self.config, 'alert_distraction_url', ''):
                _send_alert_async(self.config.alert_distraction_url)
            self._long_term_queue.clear()
            distraction_count = 0
            
        distraction_ratio = distraction_count / self.config.long_term_window_frames
        queue_size = len(self._long_term_queue)

        # 2. Update Posture
        posture_metrics = None
        if pose_landmarks and self.posture_baseline:
            posture_metrics = self._evaluate_posture(pose_landmarks, timestamp)

        return SystemEvent(
            timestamp=timestamp,
            system_state=SystemState.TRACKING,
            attention_state=self.attention_state,
            head_pose=head_pose,
            eye_state=eye_state,
            posture_metrics=posture_metrics,
            matched_zone=matched_zone,
            seconds_outside_zone=seconds_outside,
            distraction_ratio=distraction_ratio,
            queue_size=queue_size
        )

    def _matched_zone(self, pose: HeadPose, eye_state: Optional[EyeState] = None) -> Optional[AttentionZone]:
        if eye_state is not None and eye_state.irises and len(eye_state.irises) == 2:
            r1 = float(eye_state.irises[0][2])
            r2 = float(eye_state.irises[1][2])
            if pose.yaw > 20.0 and r2 > 0 and (r1 / r2) >= self.config.turn_focused_iris_ratio:
                return self.zones[0] if self.zones else None
            elif pose.yaw < -20.0 and r1 > 0 and (r2 / r1) >= self.config.turn_focused_iris_ratio:
                return self.zones[0] if self.zones else None
                
        for zone in self.zones:
            if zone.contains(pose, eye_state):
                return zone
        return None

    def _calc_distance(self, p1, p2):
        return math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
        
    def _calc_vector_angle(self, v1, v2):
        dot = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        cos_theta = dot / (norm1 * norm2)
        cos_theta = np.clip(cos_theta, -1.0, 1.0)
        return math.degrees(math.acos(cos_theta))

    def _evaluate_posture(self, landmarks, timestamp: float) -> PostureMetrics:
        L_ear = [landmarks.landmark[7].x, landmarks.landmark[7].y, landmarks.landmark[7].z]
        R_ear = [landmarks.landmark[8].x, landmarks.landmark[8].y, landmarks.landmark[8].z]
        L_shoulder = [landmarks.landmark[11].x, landmarks.landmark[11].y, landmarks.landmark[11].z]
        R_shoulder = [landmarks.landmark[12].x, landmarks.landmark[12].y, landmarks.landmark[12].z]
        
        P_ear = np.array([(L_ear[0]+R_ear[0])/2, (L_ear[1]+R_ear[1])/2, (L_ear[2]+R_ear[2])/2])
        P_shoulder = np.array([(L_shoulder[0]+R_shoulder[0])/2, (L_shoulder[1]+R_shoulder[1])/2, (L_shoulder[2]+R_shoulder[2])/2])
        
        V_neck = P_ear - P_shoulder
        current_d_neck = self._calc_distance(P_ear[:2], P_shoulder[:2])
        current_d_ear = self._calc_distance(L_ear[:2], R_ear[:2])
        
        base_v_neck = self.posture_baseline.get("v_baseline", V_neck)
        base_shoulder_y = self.posture_baseline.get("shoulder_y_base", P_shoulder[1])
        base_d_ear = self.posture_baseline.get("d_ear_base", current_d_ear)
        base_d_neck = self.posture_baseline.get("d_neck_base", current_d_neck)
        base_shoulder_tilt = self.posture_baseline.get("base_shoulder_tilt", 0.0)
        base_head_tilt = self.posture_baseline.get("base_head_tilt", 0.0)

        angle = self._calc_vector_angle(V_neck, base_v_neck)
        shoulder_drop = P_shoulder[1] - base_shoulder_y
        ear_ratio = current_d_ear / base_d_ear if base_d_ear else 1.0
        neck_ratio = current_d_neck / base_d_neck if base_d_neck else 1.0
        
        shoulder_tilt_dev = abs((L_shoulder[1] - R_shoulder[1]) - base_shoulder_tilt)
        head_tilt_dev = abs((L_ear[1] - R_ear[1]) - base_head_tilt)
        current_lateral_diff = max(shoulder_tilt_dev, head_tilt_dev)

        self.q_angle.append(angle)
        self.q_shoulder_drop.append(shoulder_drop)
        self.q_ear_ratio.append(ear_ratio)
        self.q_lateral_diff.append(current_lateral_diff)
        self.q_neck_ratio.append(neck_ratio)

        avg_angle = float(np.mean(self.q_angle))
        avg_shoulder_drop = float(np.mean(self.q_shoulder_drop))
        avg_ear_ratio = float(np.mean(self.q_ear_ratio))
        avg_lateral_diff = float(np.mean(self.q_lateral_diff))
        avg_neck_ratio = float(np.mean(self.q_neck_ratio))

        is_bad = False
        reasons = []

        if avg_angle > self.config.posture_forward_head_angle:
            is_bad = True
            reasons.append("Forward Head")
        if avg_shoulder_drop > self.config.posture_slouch_shoulder_drop or avg_neck_ratio < self.config.posture_slouch_neck_ratio:
            is_bad = True
            reasons.append("Slouching")
        if avg_ear_ratio > self.config.posture_too_close_ear_ratio:
            is_bad = True
            reasons.append("Too Close")
        if avg_lateral_diff > self.config.posture_lateral_tilt_diff: 
            is_bad = True
            reasons.append("Lateral Tilt")

        if is_bad:
            if self.bad_posture_start is None:
                self.bad_posture_start = timestamp
            elif timestamp - self.bad_posture_start > self.config.posture_alert_threshold_time:
                # Still bad posture
                pass
            else:
                # Waiting for threshold
                is_bad = False 
        else:
            self.bad_posture_start = None

        is_posture_bad_int = 1 if is_bad else 0
        self._posture_long_term_queue.append(is_posture_bad_int)
        
        posture_distraction_count = sum(self._posture_long_term_queue)
        if posture_distraction_count >= self.config.posture_long_term_distraction_threshold:
            if getattr(self.config, 'alert_posture_url', ''):
                _send_alert_async(self.config.alert_posture_url)
            self._posture_long_term_queue.clear()
            posture_distraction_count = 0
            
        posture_ratio = posture_distraction_count / self.config.posture_long_term_window_frames
        posture_queue_size = len(self._posture_long_term_queue)

        return PostureMetrics(
            v_neck_angle=avg_angle,
            shoulder_drop=avg_shoulder_drop,
            ear_ratio=avg_ear_ratio,
            neck_ratio=avg_neck_ratio,
            lateral_diff=avg_lateral_diff,
            is_bad_posture=is_bad,
            bad_posture_reasons=reasons,
            posture_ratio=posture_ratio,
            posture_queue_size=posture_queue_size
        )
