import { useEffect } from "react";

/** Sets the browser tab title to "<page> · StegoLab", or just "StegoLab". */
export function usePageTitle(page?: string) {
  useEffect(() => {
    document.title = page ? `${page} · StegoLab` : "StegoLab";
  }, [page]);
}
