import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getImage } from "@/api/images";
import type { ImageRecord } from "@/api/types";

/**
 * Lets other screens deep-link a pre-selected image with ?image=<id>.
 * The parameter is removed once read so a refresh starts clean.
 */
export function useImageFromQuery(onLoaded: (image: ImageRecord) => void) {
  const [searchParams, setSearchParams] = useSearchParams();
  const imageId = searchParams.get("image");
  const [loading, setLoading] = useState(Boolean(imageId));

  useEffect(() => {
    if (!imageId) return;
    let cancelled = false;

    setLoading(true);
    getImage(imageId)
      .then((image) => {
        if (!cancelled) onLoaded(image);
      })
      .catch(() => {
        /* Unknown or foreign image id: just start with nothing selected. */
      })
      .finally(() => {
        if (cancelled) return;
        setLoading(false);
        setSearchParams(
          (params) => {
            params.delete("image");
            return params;
          },
          { replace: true },
        );
      });

    return () => {
      cancelled = true;
    };
    // onLoaded is intentionally excluded: callers pass inline setters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [imageId, setSearchParams]);

  return loading;
}
