import { useCallback, useEffect, useState } from "react";

// Shared data-fetching hook: tracks loading / error and the typed 409
// "models not trained yet" state so every page can show a consistent prompt.
export function useApi(fetchFn, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [needsTraining, setNeedsTraining] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    setNeedsTraining(false);
    try {
      setData(await fetchFn());
    } catch (e) {
      if (e.code === 409) {
        setNeedsTraining(true);
        setData(null);
      } else {
        setError(e.message);
      }
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    reload();
  }, [reload]);

  return { data, loading, error, needsTraining, reload };
}
