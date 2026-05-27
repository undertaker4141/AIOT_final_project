import { useWebSocket } from '../hooks/useWebSocket';
import { StatusBadge } from '../components/StatusBadge';
import { AttentionPanel } from '../components/AttentionPanel';
import { PosturePanel } from '../components/PosturePanel';
import { VideoStream } from '../components/VideoStream';
import { ControlButtons } from '../components/ControlButtons';
import { Link } from 'react-router-dom';

const WS_URL = `ws://${window.location.host}/ws`;

const STATUS_COLOR: Record<string, string> = {
  open: 'text-emerald-400',
  connecting: 'text-yellow-400',
  closed: 'text-red-400',
};

const STATUS_LABEL: Record<string, string> = {
  open: '已連線',
  connecting: '連線中',
  closed: '已斷線',
};

export function Dashboard() {
  const { event, status } = useWebSocket(WS_URL);
  const systemState = event?.system_state ?? null;
  const isCalibrating = systemState === 'calibrating';
  const calibRemaining = isCalibrating && event?.seconds_outside_zone != null
    ? Math.ceil(event.seconds_outside_zone)
    : null;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4">
      {/* 頁首 */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-bold text-white">AIOT 監控系統</h1>
          <span className={`text-xs font-mono ${STATUS_COLOR[status]}`}>
            ● {STATUS_LABEL[status] ?? status}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge value={systemState ?? 'idle'} label="系統" />
          <StatusBadge value={event?.attention_state ?? null} label="專注" />
          <ControlButtons systemState={systemState} />
          <Link
            to="/history"
            className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600 text-sm text-slate-200 transition-colors"
          >
            歷史紀錄
          </Link>
        </div>
      </div>

      {/* 連線中提示 */}
      {status === 'connecting' && (
        <div className="mb-4 px-4 py-2 rounded-lg bg-yellow-900/40 border border-yellow-700 text-yellow-300 text-sm">
          正在連線至 Node A，請確認 Node A 已在 port 9547/9548 啟動…
        </div>
      )}

      {/* 校準提示 */}
      {isCalibrating && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-cyan-900/40 border border-cyan-600 text-cyan-200 text-sm font-semibold text-center">
          校準中，請保持正視前方
          {calibRemaining != null && `（剩餘 ${calibRemaining} 秒）`}
        </div>
      )}

      {/* 主要內容 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* 影像串流 */}
        <div className="space-y-4">
          <VideoStream />
        </div>

        {/* 數據面板 */}
        <div className="space-y-4">
          <AttentionPanel event={event} />
          <PosturePanel event={event} />
        </div>
      </div>

      {/* 最後更新時間 */}
      {event && (
        <div className="mt-3 text-xs text-slate-600 text-right font-mono">
          最後更新：{new Date(event.timestamp * 1000).toLocaleTimeString('zh-TW')}
        </div>
      )}
    </div>
  );
}
