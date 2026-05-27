import type { SystemEvent } from '../types';
import { MetricCard } from './MetricCard';

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

// 姿勢問題原因對照表（英文 key → 中文顯示）
const REASON_ZH: Record<string, string> = {
  'Forward Head': '頭部前傾',
  'Slouching': '駝背',
  'Too Close': '距離過近',
  'Lateral Tilt': '側傾',
};

function translateReasons(reasons: string[]): string {
  return reasons.map(r => REASON_ZH[r] ?? r).join('、');
}

export function PosturePanel({ event }: Props) {
  const pm = event?.posture_metrics;

  return (
    <div className="bg-slate-800/50 rounded-xl p-4 space-y-3">
      <h3 className="text-sm font-semibold text-slate-300 tracking-wide">坐姿分析</h3>

      {pm ? (
        <>
          <div className={`rounded-lg px-3 py-2 text-sm font-semibold ${pm.is_bad_posture ? 'bg-red-900/50 text-red-300 border border-red-700' : 'bg-emerald-900/30 text-emerald-300'}`}>
            {pm.is_bad_posture ? `坐姿不良：${translateReasons(pm.bad_posture_reasons)}` : '坐姿良好'}
          </div>

          <div className="grid grid-cols-2 gap-2">
            <MetricCard label="頸部角度" value={pm.v_neck_angle.toFixed(1)} unit="°" highlight={pm.bad_posture_reasons.includes('Forward Head')} />
            <MetricCard label="肩膀高低差" value={pm.shoulder_drop.toFixed(3)} highlight={pm.bad_posture_reasons.includes('Slouching')} />
            <MetricCard label="距離比例" value={pm.ear_ratio.toFixed(2)} unit="x" highlight={pm.bad_posture_reasons.includes('Too Close')} />
            <MetricCard label="側傾差值" value={pm.lateral_diff.toFixed(3)} highlight={pm.bad_posture_reasons.includes('Lateral Tilt')} />
          </div>

          <RatioBar ratio={pm.posture_ratio} label="不良坐姿率" />
        </>
      ) : (
        <div className="text-slate-500 text-sm">尚無坐姿資料</div>
      )}
    </div>
  );
}
