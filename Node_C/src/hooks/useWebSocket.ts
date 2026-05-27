import { useEffect, useRef, useState, useCallback } from 'react';
import type { SystemEvent } from '../types';

type WsStatus = 'connecting' | 'open' | 'closed';

export function useWebSocket(url: string) {
  const [event, setEvent] = useState<SystemEvent | null>(null);
  const [status, setStatus] = useState<WsStatus>('connecting');
  const wsRef = useRef<WebSocket | null>(null);
  const retryDelay = useRef(1000);
  const unmounted = useRef(false);

  const connect = useCallback(() => {
    if (unmounted.current) return;
    setStatus('connecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryDelay.current = 1000;
      setStatus('open');
    };

    ws.onmessage = (e) => {
      try {
        setEvent(JSON.parse(e.data) as SystemEvent);
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      if (unmounted.current) return;
      setStatus('closed');
      const delay = retryDelay.current;
      retryDelay.current = Math.min(delay * 2, 30000);
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, [url]);

  useEffect(() => {
    unmounted.current = false;
    connect();
    return () => {
      unmounted.current = true;
      wsRef.current?.close();
    };
  }, [connect]);

  return { event, status };
}
