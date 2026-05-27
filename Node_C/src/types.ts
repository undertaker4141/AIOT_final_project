export type SystemState = 'idle' | 'calibrating' | 'tracking';

export type AttentionState =
  | 'focused'
  | 'pending_distraction'
  | 'distracted'
  | 'no_face'
  | 'fatigued';

export interface HeadPose {
  pitch: number;
  yaw: number;
  roll: number;
}

export interface EyeState {
  ear: number;
  is_blinking: boolean;
  gaze_x: number;
  gaze_y: number;
}

export interface PostureMetrics {
  v_neck_angle: number;
  shoulder_drop: number;
  ear_ratio: number;
  neck_ratio: number;
  lateral_diff: number;
  is_bad_posture: boolean;
  bad_posture_reasons: string[];
  posture_ratio: number;
  posture_queue_size: number;
}

export interface SystemEvent {
  timestamp: number;
  system_state: SystemState;
  attention_state: AttentionState | null;
  head_pose: HeadPose | null;
  eye_state: EyeState | null;
  posture_metrics: PostureMetrics | null;
  matched_zone: string | null;
  seconds_outside_zone: number;
  distraction_ratio: number;
  queue_size: number;
}

export interface HistoryRow {
  id: number;
  timestamp: number;
  system_state: string | null;
  attention_state: string | null;
  matched_zone: string | null;
  seconds_outside_zone: number | null;
  pitch: number | null;
  yaw: number | null;
  roll: number | null;
  ear: number | null;
  gaze_x: number | null;
  gaze_y: number | null;
  is_bad_posture: number | null;
  bad_posture_reasons: string[] | null;
  distraction_ratio: number | null;
  posture_ratio: number | null;
  queue_size: number | null;
  posture_queue_size: number | null;
}
