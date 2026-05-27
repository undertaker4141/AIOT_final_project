import type { SystemState, AttentionState } from '../types';

const STATE_STYLES: Record<string, string> = {
  idle: 'bg-slate-600 text-slate-200',
  calibrating: 'bg-blue-600 text-white animate-pulse',
  tracking: 'bg-emerald-600 text-white',
  focused: 'bg-emerald-500 text-white',
  pending_distraction: 'bg-yellow-500 text-black',
  distracted: 'bg-red-600 text-white',
  no_face: 'bg-slate-500 text-white',
  fatigued: 'bg-purple-600 text-white',
};

const STATE_LABELS: Record<string, string> = {
  idle: '待機',
  calibrating: '校準中',
  tracking: '追蹤中',
  focused: '專注',
  pending_distraction: '即將分心',
  distracted: '分心',
  no_face: '未偵測到臉',
  fatigued: '疲勞',
};

interface Props {
  value: SystemState | AttentionState | string | null;
  label?: string;
}

export function StatusBadge({ value, label }: Props) {
  const style = value ? (STATE_STYLES[value] ?? 'bg-slate-700 text-slate-300') : 'bg-slate-700 text-slate-400';
  const displayText = value ? (STATE_LABELS[value] ?? value) : '—';
  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold tracking-wide ${style}`}>
      {label && <span className="opacity-70">{label}：</span>}
      {displayText}
    </span>
  );
}
