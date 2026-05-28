from __future__ import annotations

from typing import Iterable, List, Optional
import numpy as np

from .config import CombineConfig
from .models import AttentionZone, HeadPose, EyeState

class CalibrationBuffer:
    def __init__(self, config: CombineConfig) -> None:
        self.config = config
        self.head_samples: List[HeadPose] = []
        self.eye_states: List[Optional[EyeState]] = []
        self.posture_data: List[tuple] = []

    def add_face(self, pose: HeadPose, eye_state: Optional[EyeState] = None) -> None:
        self.head_samples.append(pose)
        self.eye_states.append(eye_state)
        
    def add_posture(self, v_neck, shoulder_y, d_ear, d_neck, shoulder_tilt, head_tilt) -> None:
        self.posture_data.append((v_neck, shoulder_y, d_ear, d_neck, shoulder_tilt, head_tilt))

    def build_zones(self) -> List[AttentionZone]:
        if len(self.head_samples) < 5:
            # Not enough samples, provide a default wide zone
            return [AttentionZone("default_zone", -20.0, 20.0, -30.0, 30.0)]

        poses = np.array([[s.pitch, s.yaw] for s in self.head_samples], dtype=np.float32)
        valid_gazes = [e for e in self.eye_states if e is not None and not e.is_blinking]
        
        gaze_x_min, gaze_x_max, gaze_y_min, gaze_y_max = 0.0, 1.0, 0.0, 1.0
        if valid_gazes:
            gaze_pts = np.array([[e.gaze_x, e.gaze_y] for e in valid_gazes], dtype=np.float32)
            gx_low, gy_low = np.percentile(gaze_pts, 5, axis=0)
            gx_high, gy_high = np.percentile(gaze_pts, 95, axis=0)
            gaze_x_min = float(gx_low - self.config.gaze_margin_x)
            gaze_x_max = float(gx_high + self.config.gaze_margin_x)
            gaze_y_min = float(gy_low - self.config.gaze_margin_y)
            gaze_y_max = float(gy_high + self.config.gaze_margin_y)

        gaze_bounds = (gaze_x_min, gaze_x_max, gaze_y_min, gaze_y_max)

        clusters = self._split_by_pitch(poses)
        zones = [
            self._zone_from_points(
                name=f"zone_{index + 1}",
                points=cluster,
                pitch_margin=self.config.pitch_margin_degrees,
                yaw_margin=self.config.yaw_margin_degrees,
                gaze_bounds=gaze_bounds,
            )
            for index, cluster in enumerate(clusters)
            if len(cluster) >= 5
        ]
        return zones or [self._zone_from_points("zone_1", poses, self.config.pitch_margin_degrees, self.config.yaw_margin_degrees, gaze_bounds)]

    def build_posture_baseline(self) -> dict:
        if len(self.posture_data) == 0:
            return {}
            
        v_necks, shoulder_ys, d_ears, d_necks, shoulder_tilts, head_tilts = zip(*self.posture_data)
        return {
            "v_baseline": np.mean(v_necks, axis=0),
            "shoulder_y_base": np.mean(shoulder_ys),
            "d_ear_base": np.mean(d_ears),
            "d_neck_base": np.mean(d_necks),
            "base_shoulder_tilt": np.mean(shoulder_tilts),
            "base_head_tilt": np.mean(head_tilts)
        }

    def _split_by_pitch(self, poses: np.ndarray) -> List[np.ndarray]:
        if len(poses) < self.config.min_samples_for_two_zones:
            return [poses]

        labels, centers = self._kmeans_1d(poses[:, 0], k=2)
        separation = abs(float(centers[0] - centers[1]))
        if separation < 10.0:
            return [poses]

        clusters = [poses[labels == label] for label in (0, 1)]
        clusters.sort(key=lambda points: float(np.mean(points[:, 0])))
        return clusters

    def _zone_from_points(self, name: str, points: np.ndarray, pitch_margin: float, yaw_margin: float, gaze_bounds: tuple) -> AttentionZone:
        pitch_low, yaw_low = np.percentile(points, 5, axis=0)
        pitch_high, yaw_high = np.percentile(points, 95, axis=0)
        gaze_x_min, gaze_x_max, gaze_y_min, gaze_y_max = gaze_bounds
        return AttentionZone(
            name=name,
            pitch_min=float(pitch_low - pitch_margin),
            pitch_max=float(pitch_high + pitch_margin),
            yaw_min=float(yaw_low - yaw_margin),
            yaw_max=float(yaw_high + yaw_margin),
            gaze_x_min=gaze_x_min,
            gaze_x_max=gaze_x_max,
            gaze_y_min=gaze_y_min,
            gaze_y_max=gaze_y_max,
        )

    def _kmeans_1d(self, values: Iterable[float], k: int) -> tuple[np.ndarray, np.ndarray]:
        data = np.asarray(list(values), dtype=np.float32)
        centers = np.percentile(data, np.linspace(20, 80, k)).astype(np.float32)

        for _ in range(30):
            distances = np.abs(data[:, None] - centers[None, :])
            labels = np.argmin(distances, axis=1)
            next_centers = np.array(
                [data[labels == label].mean() if np.any(labels == label) else centers[label] for label in range(k)],
                dtype=np.float32,
            )
            if np.allclose(centers, next_centers, atol=0.01):
                break
            centers = next_centers

        return labels, centers
