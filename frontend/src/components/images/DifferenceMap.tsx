import { useEffect, useRef, useState } from "react";
import { loadImageObjectUrl } from "@/api/images";
import { formatPercent } from "@/lib/format";
import { ErrorState, Spinner } from "@/components/ui/States";

/**
 * Lossy formats decode slightly differently in browsers than on the server,
 * which would make every pixel look changed, so the map is only offered
 * for lossless originals.
 */
export function supportsDifferenceMap(extensionOrMime: string | null | undefined): boolean {
  const value = (extensionOrMime ?? "").toLowerCase();
  return !/jpe?g|webp/.test(value);
}

// Pixel counts beyond this are skipped to keep the browser responsive.
const MAX_PIXELS = 16_000_000;
const TARGET_WIDTH = 900;

function loadImage(url: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error("Couldn't decode the image."));
    image.src = url;
  });
}

function pixelData(image: HTMLImageElement): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = image.naturalWidth;
  canvas.height = image.naturalHeight;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) throw new Error("Canvas is not available in this browser.");
  context.drawImage(image, 0, 0);
  return context.getImageData(0, 0, canvas.width, canvas.height);
}

/**
 * Shows where the two images differ. Changes are usually single-bit and
 * scattered, so the image is divided into small blocks and every block
 * containing at least one changed pixel is highlighted — brighter blocks
 * contain more changed pixels. Computed locally in the browser.
 */
export function DifferenceMap({ beforeId, afterId }: { beforeId: string; afterId: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<{ changed: number; total: number; block: number } | null>(null);

  useEffect(() => {
    let cancelled = false;
    const urls: string[] = [];

    (async () => {
      try {
        const [beforeUrl, afterUrl] = await Promise.all([
          loadImageObjectUrl(beforeId),
          loadImageObjectUrl(afterId),
        ]);
        urls.push(beforeUrl, afterUrl);

        const [beforeImage, afterImage] = await Promise.all([loadImage(beforeUrl), loadImage(afterUrl)]);
        if (cancelled) return;

        const width = beforeImage.naturalWidth;
        const height = beforeImage.naturalHeight;

        if (width !== afterImage.naturalWidth || height !== afterImage.naturalHeight) {
          throw new Error("The two images have different dimensions, so they can't be compared.");
        }
        if (width * height > MAX_PIXELS) {
          throw new Error("This image is too large to compare in the browser.");
        }

        const a = pixelData(beforeImage).data;
        const b = pixelData(afterImage).data;

        const block = Math.max(1, Math.ceil(width / TARGET_WIDTH));
        const columns = Math.ceil(width / block);
        const rows = Math.ceil(height / block);
        const counts = new Uint32Array(columns * rows);
        let changed = 0;

        for (let y = 0; y < height; y += 1) {
          const rowOffset = Math.floor(y / block) * columns;
          for (let x = 0; x < width; x += 1) {
            const i = (y * width + x) * 4;
            if (a[i] !== b[i] || a[i + 1] !== b[i + 1] || a[i + 2] !== b[i + 2]) {
              counts[rowOffset + Math.floor(x / block)] += 1;
              changed += 1;
            }
          }
        }

        const canvas = canvasRef.current;
        const context = canvas?.getContext("2d");
        if (!canvas || !context || cancelled) return;

        canvas.width = columns;
        canvas.height = rows;
        const output = context.createImageData(columns, rows);
        const perBlock = block * block;
        const accent = getComputedStyle(document.documentElement)
          .getPropertyValue("--accent")
          .trim()
          .split(/\s+/)
          .map(Number);

        for (let index = 0; index < counts.length; index += 1) {
          const o = index * 4;
          if (counts[index] > 0) {
            // At least 45% intensity so a single changed pixel is visible.
            const strength = 0.45 + 0.55 * Math.min(1, counts[index] / perBlock);
            output.data[o] = accent[0] * strength;
            output.data[o + 1] = accent[1] * strength;
            output.data[o + 2] = accent[2] * strength;
            output.data[o + 3] = 255;
          } else {
            output.data[o] = 18;
            output.data[o + 1] = 20;
            output.data[o + 2] = 28;
            output.data[o + 3] = 255;
          }
        }

        context.putImageData(output, 0, 0);
        setSummary({ changed, total: width * height, block });
        setStatus("ready");
      } catch (exception) {
        if (cancelled) return;
        setError(exception instanceof Error ? exception.message : "Couldn't build the map.");
        setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
      urls.forEach((url) => URL.revokeObjectURL(url));
    };
  }, [beforeId, afterId]);

  return (
    <div className="space-y-2">
      <div className="flex min-h-[12rem] items-center justify-center overflow-hidden rounded-lg border border-line bg-[#12141c] p-3">
        {status === "loading" && (
          <span className="flex items-center gap-2 text-sm text-slate-300">
            <Spinner /> Comparing pixels…
          </span>
        )}
        {status === "error" && error && <ErrorState title="Map unavailable" message={error} />}
        <canvas
          ref={canvasRef}
          className={status === "ready" ? "block max-h-[60vh] w-auto max-w-full" : "hidden"}
          style={{ imageRendering: "pixelated" }}
          role="img"
          aria-label="Map of the areas where the image was changed"
        />
      </div>
      {summary && (
        <p className="text-xs leading-relaxed text-muted">
          {summary.changed.toLocaleString()} of {summary.total.toLocaleString()} pixels changed (
          {formatPercent(summary.changed / summary.total, 3)}).{" "}
          {summary.block > 1
            ? `Each square is ${summary.block}×${summary.block} pixels; highlighted squares contain at least one changed pixel.`
            : "Highlighted pixels were changed."}
        </p>
      )}
    </div>
  );
}
