import { useEffect, useState } from 'react';
import type { HistoryRow } from '../types';

interface Params {
  start?: number;
  end?: number;
  limit?: number;
  offset?: number;
}

export function useHistory(params: Params) {
  const [data, setData] = useState<HistoryRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const qs = new URLSearchParams();
    if (params.start != null) qs.set('start', String(params.start));
    if (params.end != null) qs.set('end', String(params.end));
    if (params.limit != null) qs.set('limit', String(params.limit));
    if (params.offset != null) qs.set('offset', String(params.offset));

    setLoading(true);
    setError(null);
    fetch(`/api/history?${qs.toString()}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((rows: HistoryRow[]) => {
        setData(rows);
        setLoading(false);
      })
      .catch((e) => {
        setError(String(e));
        setLoading(false);
      });
  }, [params.start, params.end, params.limit, params.offset]);

  return { data, loading, error };
}
