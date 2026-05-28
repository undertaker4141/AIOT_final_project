from __future__ import annotations

import math
from pathlib import Path
from typing import Optional, Tuple, Any

import numpy as np

from .config import CombineConfig
from .models import HeadPose, EyeState

FACE_LANDMARK_IDS = {
    "nose_tip": 1,
    "chin": 152,
    "left_eye_outer": 33,
    "right_eye_outer": 263,
    "left_mouth": 61,
    "right_mouth": 291,
}

MODEL_POINTS = np.array(
    [
        (0.0, 0.0, 0.0),
        (0.0, 63.6, -12.5),
        (-43.3, -32.7, -26.0),
        (43.3, -32.7, -26.0),
        (-28.9, 28.9, -24.1),
        (28.9, 28.9, -24.1),
    ],
    dtype=np.float64,
)

class VisionEstimator:
    def __init__(self, config: CombineConfig) -> None:
        import mediapipe as mp
        from mediapipe.tasks.python import BaseOptions, vision

        self.config = config
        self._mp = mp
        
        # Face Landmarker setup
        model_path = Path(config.face_landmarker_model_path or "").expanduser()
        if not model_path.exists():
            raise RuntimeError(f"Face landmarker model not found at '{model_path}'.")

        options = vision.FaceLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.IMAGE,
            num_faces=1,
            min_face_detection_confidence=config.min_detection_confidence,
            min_face_presence_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence,
        )
        self._face_landmarker = vision.FaceLandmarker.create_from_options(options)

        # Pose setup
        self._pose_detector = mp.solutions.pose.Pose(
            min_detection_confidence=config.min_detection_confidence,
            min_tracking_confidence=config.min_tracking_confidence
        )

    def close(self) -> None:
        if self._face_landmarker is not None:
            self._face_landmarker.close()
        if self._pose_detector is not None:
            self._pose_detector.close()

    def estimate(self, frame_bgr: np.ndarray) -> Tuple[Optional[HeadPose], Optional[EyeState], Any, Any]:
        import cv2
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        height, width = frame_bgr.shape[:2]

        # 1. Face Landmarker
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=frame_rgb)
        face_result = self._face_landmarker.detect(mp_image)
        
        head_pose = None
        eye_state = None
        face_landmarks_data = None
        
        if face_result and face_result.face_landmarks:
            landmarks = face_result.face_landmarks[0]
            face_landmarks_data = landmarks
            
            image_points = np.array(
                [
                    (landmarks[index].x * width, landmarks[index].y * height)
                    for index in FACE_LANDMARK_IDS.values()
                ],
                dtype=np.float64,
            )

            focal_length = float(width)
            camera_matrix = np.array(
                [
                    [focal_length, 0.0, width / 2.0],
                    [0.0, focal_length, height / 2.0],
                    [0.0, 0.0, 1.0],
                ],
                dtype=np.float64,
            )
            distortion = np.zeros((4, 1), dtype=np.float64)

            success, rotation_vector, _ = cv2.solvePnP(
                MODEL_POINTS, image_points, camera_matrix, distortion, flags=cv2.SOLVEPNP_ITERATIVE
            )
            if success:
                rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
                angles = self._rotation_matrix_to_euler_angles(rotation_matrix)
                head_pose = HeadPose(pitch=angles[0], yaw=angles[1], roll=angles[2])

            if len(landmarks) >= 478:
                right_ear = self._calculate_ear(landmarks, [33, 160, 158, 133, 153, 144])
                left_ear = self._calculate_ear(landmarks, [362, 385, 387, 263, 373, 380])
                avg_ear = float((right_ear + left_ear) / 2.0)
                is_blinking = avg_ear < self.config.ear_threshold

                def get_3d_pt(idx):
                    return np.array([landmarks[idx].x * width, landmarks[idx].y * height, landmarks[idx].z * width])

                p_inner = get_3d_pt(133)
                p_outer = get_3d_pt(33)
                p_center = get_3d_pt(468)
                
                p_mid = (p_inner + p_outer) / 2.0
                r = np.linalg.norm(p_inner - p_outer) / 2.0
                p_eyeball_center = p_mid.copy()
                p_eyeball_center[2] += r
                
                gaze_vector = p_center - p_eyeball_center
                gaze_vector = gaze_vector / np.linalg.norm(gaze_vector)
                
                gaze_x = float(np.clip(gaze_vector[0] * 1.5 + 0.5, 0.0, 1.0))
                gaze_y = float(np.clip(gaze_vector[1] * 3.5 + 0.75, 0.0, 1.0))

                irises = []
                for center_idx, edge_idx in [(468, 469), (473, 474)]:
                    cx = int(landmarks[center_idx].x * width)
                    cy = int(landmarks[center_idx].y * height)
                    ex = int(landmarks[edge_idx].x * width)
                    ey = int(landmarks[edge_idx].y * height)
                    r_size = int(np.sqrt((cx - ex)**2 + (cy - ey)**2))
                    irises.append((cx, cy, r_size))
                    
                iris_ratio = 1.0
                if len(irises) == 2:
                    r1 = float(irises[0][2])
                    r2 = float(irises[1][2])
                    if min(r1, r2) > 0:
                        iris_ratio = max(r1, r2) / min(r1, r2)

                eye_state = EyeState(
                    ear=avg_ear,
                    is_blinking=is_blinking,
                    gaze_x=gaze_x,
                    gaze_y=gaze_y,
                    irises=irises,
                    iris_ratio=iris_ratio
                )

        # 2. Body Pose
        frame_rgb.flags.writeable = False
        pose_result = self._pose_detector.process(frame_rgb)
        
        pose_landmarks_data = pose_result.pose_landmarks if pose_result else None

        return head_pose, eye_state, face_landmarks_data, pose_landmarks_data

    def _rotation_matrix_to_euler_angles(self, rotation_matrix: np.ndarray) -> tuple[float, float, float]:
        import cv2
        projection = np.hstack((rotation_matrix, np.zeros((3, 1), dtype=np.float64)))
        _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(projection)
        pitch, yaw, roll = euler.flatten()
        return float(pitch), float(yaw), float(roll)

    def _calculate_ear(self, landmarks, eye_indices: list[int]) -> float:
        p1 = np.array([landmarks[eye_indices[0]].x, landmarks[eye_indices[0]].y])
        p2 = np.array([landmarks[eye_indices[1]].x, landmarks[eye_indices[1]].y])
        p3 = np.array([landmarks[eye_indices[2]].x, landmarks[eye_indices[2]].y])
        p4 = np.array([landmarks[eye_indices[3]].x, landmarks[eye_indices[3]].y])
        p5 = np.array([landmarks[eye_indices[4]].x, landmarks[eye_indices[4]].y])
        p6 = np.array([landmarks[eye_indices[5]].x, landmarks[eye_indices[5]].y])

        dist_v1 = np.linalg.norm(p2 - p6)
        dist_v2 = np.linalg.norm(p3 - p5)
        dist_h = np.linalg.norm(p1 - p4)

        return float((dist_v1 + dist_v2) / (2.0 * dist_h))
