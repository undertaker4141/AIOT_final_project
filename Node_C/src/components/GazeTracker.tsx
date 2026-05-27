import type { EyeState, AttentionState } from '../types';

interface Props {
  eyeState: EyeState | null;
  attentionState: AttentionState | null;
}

const SIZE = 120;

export function GazeTracker({ eyeState, attentionState }: Props) {
  const isDistracted =
    attentionState === 'distracted' || attentionState === 'pending_distraction';
  const dotColor = isDistracted ? '#ef4444' : '#22c55e';

  const gx = eyeState ? eyeState.gaze_x * SIZE : SIZE / 2;
  const gy = eyeState ? eyeState.gaze_y * SIZE : SIZE / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="text-xs text-slate-400">視線追蹤</div>
      <svg width={SIZE} height={SIZE} className="rounded border border-slate-600 bg-slate-900">
        {/* 十字準線 */}
        <line x1={SIZE / 2} y1={0} x2={SIZE / 2} y2={SIZE} stroke="#334155" strokeWidth={1} />
        <line x1={0} y1={SIZE / 2} x2={SIZE} y2={SIZE / 2} stroke="#334155" strokeWidth={1} />
        {/* 視線點 */}
        {eyeState && (
          <circle
            cx={Math.max(4, Math.min(SIZE - 4, gx))}
            cy={Math.max(4, Math.min(SIZE - 4, gy))}
            r={5}
            fill={dotColor}
          />
        )}
      </svg>
    </div>
  );
}
