import { useId, useState } from "react";
import { useImageObjectUrl } from "@/hooks/useImageObjectUrl";
import { ErrorState, Spinner } from "@/components/ui/States";

/**
 * Before/after view: drag (or use arrow keys on) the divider to reveal the
 * original image on the left and the image with the hidden message on
 * the right.
 */
export function CompareSlider({
  beforeId,
  afterId,
  width,
  height,
  beforeLabel = "Original",
  afterLabel = "With message",
}: {
  beforeId: string;
  afterId: string;
  width: number;
  height: number;
  beforeLabel?: string;
  afterLabel?: string;
}) {
  const before = useImageObjectUrl(beforeId);
  const after = useImageObjectUrl(afterId);
  const [position, setPosition] = useState(50);
  const sliderId = useId();

  const loading = before.loading || after.loading;
  const error = before.error ?? after.error;

  return (
    <div className="checkerboard flex items-center justify-center overflow-hidden rounded-lg border border-line p-3">
      {error && <ErrorState title="Preview unavailable" message={error} />}
      {!error && loading && (
        <div className="flex min-h-[16rem] items-center gap-2 text-sm text-muted">
          <Spinner /> Loading images…
        </div>
      )}
      {!error && !loading && before.url && after.url && (
        <div
          className="relative w-full max-w-full select-none overflow-hidden rounded shadow-raised"
          style={{
            aspectRatio: `${width} / ${height}`,
            maxHeight: "60vh",
            width: `min(100%, calc(60vh * ${width / height}))`,
          }}
        >
          {/* image-orientation: none shows stored pixels exactly as the
              server processed them (no EXIF rotation), keeping both aligned. */}
          <img
            src={after.url}
            alt={afterLabel}
            className="absolute inset-0 h-full w-full object-fill"
            style={{ imageOrientation: "none" }}
            draggable={false}
          />
          <img
            src={before.url}
            alt={beforeLabel}
            className="absolute inset-0 h-full w-full object-fill"
            style={{ clipPath: `inset(0 ${100 - position}% 0 0)`, imageOrientation: "none" }}
            draggable={false}
          />

          <div className="pointer-events-none absolute inset-y-0" style={{ left: `${position}%` }} aria-hidden>
            <div className="absolute inset-y-0 -ml-px w-0.5 bg-white shadow-[0_0_0_1px_rgb(0_0_0/0.25)]" />
            <div className="absolute top-1/2 -ml-4 -mt-4 flex h-8 w-8 items-center justify-center rounded-full border border-black/10 bg-white text-xs font-bold text-slate-700 shadow-raised">
              ⇆
            </div>
          </div>

          <span className="pointer-events-none absolute left-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs font-medium text-white">
            {beforeLabel}
          </span>
          <span className="pointer-events-none absolute right-2 top-2 rounded bg-black/60 px-2 py-0.5 text-xs font-medium text-white">
            {afterLabel}
          </span>

          <label htmlFor={sliderId} className="sr-only">
            Comparison position: left shows {beforeLabel.toLowerCase()}, right shows {afterLabel.toLowerCase()}
          </label>
          <input
            id={sliderId}
            type="range"
            min={0}
            max={100}
            value={position}
            onChange={(event) => setPosition(Number(event.target.value))}
            className="absolute inset-0 h-full w-full cursor-ew-resize opacity-0"
          />
        </div>
      )}
    </div>
  );
}
