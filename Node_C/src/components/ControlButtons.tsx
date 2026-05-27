import { useState } from 'react';

interface Props {
  systemState?: string | null;
}

export function ControlButtons({ systemState }: Props) {
  const [loading, setLoading] = useState<'start' | 'end' | null>(null);
  const [error, setError] = useState<string | null>(null);

  const isActive = systemState === 'calibrating' || systemState === 'tracking';

  const call = async (endpoint: 'start' | 'end') => {
    setLoading(endpoint);
    setError(null);
    try {
      const res = await fetch(`/${endpoint}`);
      if (!res.ok) setError(`操作失敗：HTTP ${res.status}`);
    } catch (e) {
      setError(`操作失敗：網路錯誤`);
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="flex flex-col gap-1">
      <div className="flex gap-3">
        <button
          onClick={() => call('start')}
          disabled={loading !== null || isActive}
          title={isActive ? '系統已在運行中' : '開始監控'}
          className="px-5 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors"
        >
          {loading === 'start' ? '啟動中…' : '開始'}
        </button>
        <button
          onClick={() => call('end')}
          disabled={loading !== null}
          className="px-5 py-2 rounded-lg bg-red-700 hover:bg-red-600 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors"
        >
          {loading === 'end' ? '停止中…' : '結束'}
        </button>
      </div>
      {error && (
        <span className="text-xs text-red-400 font-mono">{error}</span>
      )}
    </div>
  );
}
