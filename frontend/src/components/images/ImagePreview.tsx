import { useState } from "react";
import { ImageOff, Maximize2, ZoomIn, ZoomOut } from "lucide-react";
import { useImageObjectUrl } from "@/hooks/useImageObjectUrl";
import { cn } from "@/lib/cn";
import type { SuspiciousRegion } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { EmptyState, ErrorState, Spinner } from "@/components/ui/States";

/** Colour ramp from accent to red as the anomaly score rises. */
export function regionTone(score: number | null): string {
  if (score === null) return "rgb(var(--faint))";
  if (score >= 0.66) return "rgb(var(--stego))";
  if (score >= 0.33) return "rgb(var(--warn))";
  return "rgb(var(--accent))";
}

export function regionKey(region: SuspiciousRegion, index: number): string {
  return region.id ?? `${region.x}-${region.y}-${index}`;
}

/** Zoomable preview of a stored image, with optional region overlays. */
export function ImagePreview({
  imageId,
  alt = "Image preview",
  width,
  height,
  regions = [],
  showRegions = true,
  highlightedRegionId,
  onRegionHover,
  className,
  emptyText = "Choose an image to preview it here.",
}: {
  imageId: string | null | undefined;
  alt?: string;
  /** Natural size; needed to place region overlays. */
  width?: number;
  height?: number;
  regions?: SuspiciousRegion[];
  showRegions?: boolean;
  highlightedRegionId?: string | null;
  onRegionHover?: (regionId: string | null) => void;
  className?: string;
  emptyText?: string;
}) {
  const { url, loading, error } = useImageObjectUrl(imageId);
  const [zoom, setZoom] = useState(1);

  // Overlays use percentages of the natural size so they stay aligned.
  const canOverlay =
    showRegions && regions.length > 0 && Boolean(width && height && width > 0 && height > 0);

  return (
    <div
      className={cn(
        "checkerboard relative flex min-h-[16rem] items-center justify-center overflow-auto rounded-lg border border-line p-4",
        className,
      )}
    >
      {!imageId && (
        <EmptyState icon={<ImageOff className="h-5 w-5" />} title="No image yet" description={emptyText} />
      )}

      {imageId && loading && (
        <div className="flex flex-col items-center gap-2 text-sm text-muted">
          <Spinner className="h-5 w-5" />
          Loading preview…
        </div>
      )}

      {imageId && error && <ErrorState title="Preview unavailable" message={error} />}

      {imageId && url && !loading && !error && (
        <div
          className="relative shrink-0 transition-transform duration-200"
          style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}
        >
          <img
            src={url}
            alt={alt}
            className="block max-h-[60vh] w-auto max-w-full rounded shadow-raised"
            // Raw pixel orientation: region coordinates come from the server,
            // which ignores EXIF rotation.
            style={{ imageRendering: zoom > 1.8 ? "pixelated" : "auto", imageOrientation: "none" }}
          />

          {canOverlay && (
            <div className="pointer-events-none absolute inset-0">
              {regions.map((region, index) => {
                const key = regionKey(region, index);
                const active = highlightedRegionId === key;
                const tone = regionTone(region.suspicion_score);

                return (
                  <div
                    key={key}
                    onMouseEnter={() => onRegionHover?.(key)}
                    onMouseLeave={() => onRegionHover?.(null)}
                    className={cn(
                      "pointer-events-auto absolute rounded-[2px] border-2 transition-opacity",
                      active ? "opacity-100" : "opacity-70",
                    )}
                    style={{
                      left: `${(region.x / width!) * 100}%`,
                      top: `${(region.y / height!) * 100}%`,
                      width: `${(region.width / width!) * 100}%`,
                      height: `${(region.height / height!) * 100}%`,
                      borderColor: tone,
                      boxShadow: active ? `0 0 0 3px ${tone}` : undefined,
                    }}
                    title={`Area ${index + 1} — anomaly score ${region.suspicion_score?.toFixed(3) ?? "n/a"}`}
                  >
                    <span
                      className="absolute left-0 top-0 -translate-y-full rounded-sm px-1 text-[10px] font-semibold leading-tight text-white"
                      style={{ backgroundColor: tone }}
                    >
                      {index + 1}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {url && (
        <div className="absolute right-2 top-2 flex items-center gap-0.5 rounded-lg border border-line bg-surface/95 p-1 shadow-sm">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Zoom out"
            onClick={() => setZoom((z) => Math.max(0.25, +(z - 0.25).toFixed(2)))}
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <span className="min-w-[2.75rem] text-center font-mono text-xs tabular-nums text-muted" aria-live="polite">
            {Math.round(zoom * 100)}%
          </span>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Zoom in"
            onClick={() => setZoom((z) => Math.min(6, +(z + 0.25).toFixed(2)))}
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
          <Button variant="ghost" size="icon" className="h-7 w-7" aria-label="Reset zoom" onClick={() => setZoom(1)}>
            <Maximize2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
