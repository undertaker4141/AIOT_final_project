import { useState } from 'react';

export function VideoStream() {
  const [error, setError] = useState(false);

  if (error) {
    return (
      <div className="w-full aspect-video bg-slate-900 rounded-xl flex items-center justify-center border border-slate-700">
        <div className="text-center text-slate-500">
          <div className="text-2xl mb-2">📷</div>
          <div className="text-sm">串流無法連線</div>
          <button
            className="mt-2 text-xs text-blue-400 underline"
            onClick={() => setError(false)}
          >
            重試
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full rounded-xl overflow-hidden border border-slate-700 bg-black">
      <img
        src="/stream.mjpg"
        alt="即時串流"
        className="w-full block"
        onError={() => setError(true)}
      />
    </div>
  );
}
