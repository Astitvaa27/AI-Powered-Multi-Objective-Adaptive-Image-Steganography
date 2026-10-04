import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError } from "@/api/client";

/**
 * Runs an async loader on mount (and whenever `deps` change) and exposes
 * data / loading / error / reload. Stale responses are ignored.
 */
export function useAsync<T>(
  loader: () => Promise<T>,
  deps: unknown[],
  fallbackError = "Something went wrong while loading this data.",
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const requestId = useRef(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  const reload = useCallback(async () => {
    const id = ++requestId.current;
    setLoading(true);
    setError(null);

    try {
      const result = await run();
      if (id === requestId.current) setData(result);
    } catch (exception) {
      if (id === requestId.current) {
        setError(exception instanceof ApiError ? exception.message : fallbackError);
      }
    } finally {
      if (id === requestId.current) setLoading(false);
    }
  }, [run, fallbackError]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { data, loading, error, reload, setData };
}

/** Read an ApiError (or anything thrown) as a user-facing message. */
export function errorMessage(exception: unknown, fallback: string): string {
  return exception instanceof ApiError ? exception.message : fallback;
}
