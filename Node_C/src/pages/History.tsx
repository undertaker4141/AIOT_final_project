import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useHistory } from '../hooks/useHistory';
import type { HistoryRow } from '../types';

const PAGE_SIZE = 50;

function toLocalDatetimeValue(ts: number) {
  const d = new Date(ts * 1000);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalDatetimeValue(s: string): number {
  return new Date(s).getTime() / 1000;
}

const ATTENTION_ZH: Record<string, string> = {
  focused: '專注',
  pending_distraction: '即將分心',
  distracted: '分心',
  no_face: '未偵測到臉',
  fatigued: '疲勞',
};

export function History() {
  const now = Date.now() / 1000;
  const [startStr, setStartStr] = useState(toLocalDatetimeValue(now - 3600));
  const [endStr, setEndStr] = useState(toLocalDatetimeValue(now));
  const [offset, setOffset] = useState(0);

  const params = useMemo(() => ({
    start: fromLocalDatetimeValue(startStr),
    end: fromLocalDatetimeValue(endStr),
    limit: PAGE_SIZE,
    offset,
  }), [startStr, endStr, offset]);

  const { data, loading, error } = useHistory(params);

  const chartData = useMemo(() =>
    [...data].reverse().map((row: HistoryRow) => ({
      time: new Date(row.timestamp * 1000).toLocaleTimeString('zh-TW'),
      distraction: row.distraction_ratio != null ? +(row.distraction_ratio * 100).toFixed(1) : null,
      posture: row.posture_ratio != null ? +(row.posture_ratio * 100).toFixed(1) : null,
    })),
    [data]
  );

  const xAxisInterval = chartData.length > 8 ? Math.floor(chartData.length / 8) : 0;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      <div className="flex items-center gap-4 mb-6">
        <Link to="/" className="text-blue-400 hover:text-blue-300 text-sm">← 返回儀表板</Link>
        <h1 className="text-lg font-bold text-white">歷史紀錄</h1>
      </div>

      {/* 篩選條件 */}
      <div className="flex flex-wrap gap-4 mb-6 bg-slate-800 rounded-xl p-4">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">開始時間</label>
          <input
            type="datetime-local"
            value={startStr}
            onChange={(e) => { setStartStr(e.target.value); setOffset(0); }}
            className="bg-slate-700 text-slate-100 rounded px-2 py-1 text-sm border border-slate-600"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">結束時間</label>
          <input
            type="datetime-local"
            value={endStr}
            onChange={(e) => { setEndStr(e.target.value); setOffset(0); }}
            className="bg-slate-700 text-slate-100 rounded px-2 py-1 text-sm border border-slate-600"
          />
        </div>
        <div className="flex items-end">
          <button
            onClick={() => {
              const n = Date.now() / 1000;
              setStartStr(toLocalDatetimeValue(n - 3600));
              setEndStr(toLocalDatetimeValue(n));
              setOffset(0);
            }}
            className="px-4 py-1.5 bg-blue-700 hover:bg-blue-600 rounded text-sm text-white"
          >
            最近一小時
          </button>
        </div>
      </div>

      {/* 圖表 */}
      {loading && <div className="text-slate-400 text-sm mb-4">載入中…</div>}
      {error && <div className="text-red-400 text-sm mb-4">錯誤：{error}</div>}

      {chartData.length > 0 && (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-6">
          <div className="bg-slate-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">分心率 (%)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#94a3b8' }} interval={xAxisInterval} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', color: '#e2e8f0' }} />
                <Line type="monotone" dataKey="distraction" name="分心率" stroke="#ef4444" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-slate-800 rounded-xl p-4">
            <h3 className="text-sm font-semibold text-slate-300 mb-3">不良坐姿率 (%)</h3>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#94a3b8' }} interval={xAxisInterval} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#94a3b8' }} />
                <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #475569', color: '#e2e8f0' }} />
                <Line type="monotone" dataKey="posture" name="不良坐姿率" stroke="#f59e0b" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* 資料表格 */}
      {data.length > 0 && (
        <div className="bg-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="bg-slate-700 text-slate-300">
                  <th className="px-3 py-2 text-left">時間</th>
                  <th className="px-3 py-2 text-left">專注狀態</th>
                  <th className="px-3 py-2 text-right">俯仰角</th>
                  <th className="px-3 py-2 text-right">偏航角</th>
                  <th className="px-3 py-2 text-right">EAR</th>
                  <th className="px-3 py-2 text-left">坐姿</th>
                  <th className="px-3 py-2 text-right">分心率</th>
                  <th className="px-3 py-2 text-right">不良坐姿率</th>
                </tr>
              </thead>
              <tbody>
                {data.map((row) => (
                  <tr key={row.id} className="border-t border-slate-700 hover:bg-slate-700/30">
                    <td className="px-3 py-1.5 font-mono text-slate-400">
                      {new Date(row.timestamp * 1000).toLocaleTimeString('zh-TW')}
                    </td>
                    <td className="px-3 py-1.5">
                      {row.attention_state ? (ATTENTION_ZH[row.attention_state] ?? row.attention_state) : '—'}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">{row.pitch?.toFixed(1) ?? '—'}</td>
                    <td className="px-3 py-1.5 text-right font-mono">{row.yaw?.toFixed(1) ?? '—'}</td>
                    <td className="px-3 py-1.5 text-right font-mono">{row.ear?.toFixed(3) ?? '—'}</td>
                    <td className="px-3 py-1.5">
                      {row.is_bad_posture
                        ? <span className="text-red-400">不良</span>
                        : <span className="text-emerald-400">良好</span>}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">
                      {row.distraction_ratio != null ? `${(row.distraction_ratio * 100).toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-3 py-1.5 text-right font-mono">
                      {row.posture_ratio != null ? `${(row.posture_ratio * 100).toFixed(1)}%` : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 分頁 */}
          <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
            <span className="text-xs text-slate-400">共 {data.length} 筆</span>
            <div className="flex gap-2">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-40 rounded"
              >
                上一頁
              </button>
              <button
                disabled={data.length < PAGE_SIZE}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="px-3 py-1 text-xs bg-slate-700 hover:bg-slate-600 disabled:opacity-40 rounded"
              >
                下一頁
              </button>
            </div>
          </div>
        </div>
      )}

      {!loading && data.length === 0 && (
        <div className="text-slate-500 text-sm text-center py-12">所選時間範圍內無資料</div>
      )}
    </div>
  );
}
