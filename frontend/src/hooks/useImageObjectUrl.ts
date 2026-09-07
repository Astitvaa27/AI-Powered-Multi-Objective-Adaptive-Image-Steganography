import { useEffect, useState } from "react";
import { loadImageObjectUrl } from "@/api/images";

/**
 * Loads an authenticated image preview and revokes the object URL when
 * the component unmounts or the image changes.
 */
export function useImageObjectUrl(imageId: string | null | undefined) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!imageId) {
      setUrl(null);
      setError(null);
      return;
    }

    let cancelled = false;
    let created: string | null = null;

    setLoading(true);
    setError(null);

    loadImageObjectUrl(imageId)
      .then((objectUrl) => {
        if (cancelled) {
          URL.revokeObjectURL(objectUrl);
          return;
        }
        created = objectUrl;
        setUrl(objectUrl);
      })
      .catch((exception: unknown) => {
        if (!cancelled) {
          setError(
            exception instanceof Error
              ? exception.message
              : "Unable to load image preview.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
      if (created) URL.revokeObjectURL(created);
    };
  }, [imageId]);

  return { url, loading, error };
}
