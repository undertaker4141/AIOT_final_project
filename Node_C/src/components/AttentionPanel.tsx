import type { SystemEvent } from '../types';
import { MetricCard } from './MetricCard';
import { GazeTracker } from './GazeTracker';

interface Props {
  event: SystemEvent | null;
}

function RatioBar({ ratio, label }: { ratio: number; label: string }) {
  const pct = Math.min(100, ratio * 100);
  const color = pct > 40 ? 'bg-red-500' : pct > 25 ? 'bg-yellow-500' : 'bg-emerald-500';
  return (
    <div>
      <div className="flex justify-between text-xs text-slate-400 mb-1">
        <span>{label}</span>
        <span>{pct.toFixed(1)}%</span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export function AttentionPanel({ event }: Props) {
  const hp = event?.head_pose;
  const es = event?.eye_state;

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
      <h3 className="text-sm font-semibold text-slate-300 tracking-wide">專注度分析</h3>

      <div className="grid grid-cols-3 gap-2">
        <MetricCard label="俯仰角" value={hp ? hp.pitch.toFixed(1) : null} unit="°" />
        <MetricCard label="偏航角" value={hp ? hp.yaw.toFixed(1) : null} unit="°" />
        <MetricCard label="翻滾角" value={hp ? hp.roll.toFixed(1) : null} unit="°" />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricCard label="眼睛開合度 (EAR)" value={es ? es.ear.toFixed(3) : null} />
        <MetricCard label="離開專注區時間" value={event ? event.seconds_outside_zone.toFixed(1) : null} unit="秒" />
      </div>

      <div className="flex items-center gap-4">
        <GazeTracker eyeState={es ?? null} attentionState={event?.attention_state ?? null} />
        <div className="flex-1 space-y-2">
          <MetricCard label="對應區域" value={event?.matched_zone ?? '無'} />
          <MetricCard label="佇列大小" value={event?.queue_size ?? null} />
        </div>
      </div>

      <RatioBar ratio={event?.distraction_ratio ?? 0} label="分心率" />
    </div>
  );
}
