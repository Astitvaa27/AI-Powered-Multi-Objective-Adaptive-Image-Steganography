import { useState } from "react";
import {
  ImageOff,
  Maximize2,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useImageObjectUrl } from "@/hooks/useImageObjectUrl";
import { cn } from "@/lib/cn";
import { formatBytes } from "@/lib/format";
import type { ImageRecord, SuspiciousRegion } from "@/api/types";
import { Button } from "./ui/Button";
import { EmptyState, ErrorState, Spinner } from "./ui/States";

interface ImagePreviewProps {
  imageId: string | null | undefined;
  /** Metadata shown beneath the canvas; optional. */
  meta?: Pick<
    ImageRecord,
    "original_filename" | "width" | "height" | "channels" | "file_size_bytes" | "file_extension"
  > | null;
  regions?: SuspiciousRegion[];
  /** Natural dimensions, needed to place region overlays correctly. */
  naturalWidth?: number;
  naturalHeight?: number;
  highlightedRegionId?: string | null;
  onRegionHover?: (regionId: string | null) => void;
  showRegions?: boolean;
  className?: string;
  minHeightClass?: string;
}

/** Colour ramp from amber to red as the suspicion score rises. */
function regionTone(score: number | null): string {
  if (score === null) return "rgb(var(--faint))";
  if (score >= 0.66) return "rgb(var(--stego))";
  if (score >= 0.33) return "rgb(var(--warn))";
  return "rgb(var(--accent))";
}

export function ImagePreview({
  imageId,
  meta,
  regions = [],
  naturalWidth,
  naturalHeight,
  highlightedRegionId,
  onRegionHover,
  showRegions = true,
  className,
  minHeightClass = "min-h-[26rem]",
}: ImagePreviewProps) {
  const { url, loading, error } = useImageObjectUrl(imageId);
  const [zoom, setZoom] = useState(1);

  const width = naturalWidth ?? meta?.width;
  const height = naturalHeight ?? meta?.height;

  // Overlays are positioned in percentages of the natural image size, so
  // they stay aligned at any rendered scale.
  const canOverlay =
    showRegions &&
    regions.length > 0 &&
    Boolean(width && height && width > 0 && height > 0);

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div
        className={cn(
          "checkerboard relative flex flex-1 items-center justify-center overflow-auto rounded-lg border border-line bg-elevated/40 p-4",
          minHeightClass,
        )}
      >
        {!imageId && (
          <EmptyState
            icon={<ImageOff className="h-5 w-5" />}
            title="No image selected"
            description="Upload a new image or pick one from your library to preview it here."
          />
        )}

        {imageId && loading && (
          <div className="flex flex-col items-center gap-2 text-xs text-muted">
            <Spinner className="h-5 w-5" />
            Loading preview…
          </div>
        )}

        {imageId && error && <ErrorState message={error} />}

        {imageId && url && !loading && !error && (
          <div
            className="relative shrink-0 transition-transform duration-200"
            style={{ transform: `scale(${zoom})`, transformOrigin: "center" }}
          >
            <img
              src={url}
              alt={meta?.original_filename ?? "Selected image"}
              className="block max-h-[70vh] w-auto max-w-full rounded shadow-panel"
              style={{ imageRendering: zoom > 1.8 ? "pixelated" : "auto" }}
            />

            {canOverlay && (
              <div className="pointer-events-none absolute inset-0">
                {regions.map((region, index) => {
                  const key = region.id ?? `${region.x}-${region.y}-${index}`;
                  const active = highlightedRegionId === key;

                  return (
                    <div
                      key={key}
                      onMouseEnter={() => onRegionHover?.(key)}
                      onMouseLeave={() => onRegionHover?.(null)}
                      className={cn(
                        "pointer-events-auto absolute rounded-[2px] border-2 transition-all",
                        active ? "opacity-100" : "opacity-70",
                      )}
                      style={{
                        left: `${(region.x / width!) * 100}%`,
                        top: `${(region.y / height!) * 100}%`,
                        width: `${(region.width / width!) * 100}%`,
                        height: `${(region.height / height!) * 100}%`,
                        borderColor: regionTone(region.suspicion_score),
                        boxShadow: active
                          ? `0 0 0 3px ${regionTone(region.suspicion_score)}33`
                          : undefined,
                      }}
                      title={`Candidate region #${index + 1} — anomaly score ${
                        region.suspicion_score?.toFixed(3) ?? "n/a"
                      }`}
                    >
                      <span
                        className="absolute -top-0.5 left-0 -translate-y-full rounded px-1 text-[9px] font-semibold leading-tight text-white"
                        style={{ backgroundColor: regionTone(region.suspicion_score) }}
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
          <div className="absolute right-3 top-3 flex items-center gap-1 rounded-lg border border-line bg-surface/90 p-1 backdrop-blur">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Zoom out"
              onClick={() => setZoom((z) => Math.max(0.25, +(z - 0.25).toFixed(2)))}
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </Button>
            <span className="min-w-[3rem] text-center font-mono text-[11px] tabular-nums text-muted">
              {Math.round(zoom * 100)}%
            </span>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Zoom in"
              onClick={() => setZoom((z) => Math.min(6, +(z + 0.25).toFixed(2)))}
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 w-7 p-0"
              aria-label="Fit to screen"
              onClick={() => setZoom(1)}
            >
              <Maximize2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        )}
      </div>

      {meta && (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-4">
          <div className="min-w-0">
            <dt className="text-faint">File</dt>
            <dd className="truncate font-medium text-fg" title={meta.original_filename}>
              {meta.original_filename}
            </dd>
          </div>
          <div>
            <dt className="text-faint">Dimensions</dt>
            <dd className="font-mono text-fg">
              {meta.width} × {meta.height}
            </dd>
          </div>
          <div>
            <dt className="text-faint">Channels</dt>
            <dd className="font-mono text-fg">{meta.channels}</dd>
          </div>
          <div>
            <dt className="text-faint">Size</dt>
            <dd className="font-mono text-fg">
              {formatBytes(meta.file_size_bytes)}
              <span className="ml-1 text-faint">{meta.file_extension}</span>
            </dd>
          </div>
        </dl>
      )}
    </div>
  );
}
