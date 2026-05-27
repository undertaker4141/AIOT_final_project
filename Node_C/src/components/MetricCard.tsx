interface Props {
  label: string;
  value: string | number | null | undefined;
  unit?: string;
  highlight?: boolean;
}

export function MetricCard({ label, value, unit, highlight }: Props) {
  return (
    <div className={`rounded-lg p-3 ${highlight ? 'bg-red-900/40 border border-red-700' : 'bg-slate-800'}`}>
      <div className="text-xs text-slate-400 mb-1">{label}</div>
      <div className="text-lg font-mono font-semibold text-slate-100">
        {value != null ? value : '—'}
        {unit && <span className="text-xs text-slate-400 ml-1">{unit}</span>}
      </div>
    </div>
  );
}
