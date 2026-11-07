"use client";

import { useCallback, useEffect, useRef, useState } from "react";

interface PollingOptions {
  intervalMs?: number;
  enabled?: boolean;
}

/**
 * Fetches once on mount (and whenever `deps` change), then re-polls on an interval.
 * `loading` is only true until the first response so polling never flashes skeletons.
 */
export function usePolling<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList,
  { intervalMs, enabled = true }: PollingOptions = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    try {
      const result = await fetcherRef.current();
      setData(result);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    setLoading(true);
    refresh();
    if (!intervalMs) return;
    const id = setInterval(refresh, intervalMs);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, refresh, ...deps]);

  return { data, error, loading, refresh };
}
