import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
} from "react";
import {
  FolderOpen,
  HardDriveDownload,
  Image as ImageIcon,
  Search,
  Upload,
  X,
} from "lucide-react";
import { listImages, registerImagePath, uploadImage } from "@/api/images";
import type { ImageRecord } from "@/api/types";
import { errorMessage } from "@/hooks/useAsync";
import { useImageObjectUrl } from "@/hooks/useImageObjectUrl";
import { imageKindLabel } from "@/lib/describe";
import { cn } from "@/lib/cn";
import { formatBytes, formatRelative } from "@/lib/format";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Field, Input } from "@/components/ui/Field";
import { SegmentedControl } from "@/components/ui/Tabs";
import { EmptyState, ErrorState, SkeletonRows, Spinner } from "@/components/ui/States";

type ImageKind = "COVER" | "SUSPECT" | "STEGO";

const ACCEPT = ".png,.jpg,.jpeg,.bmp,.tif,.tiff,.pgm,.ppm,.webp";
const MAX_UPLOAD_BYTES = 25 * 1024 * 1024;
const PAGE_SIZE = 50;

/** Small authenticated thumbnail for the selected image. */
function Thumbnail({ imageId, alt }: { imageId: string; alt: string }) {
  const { url, loading } = useImageObjectUrl(imageId);

  return (
    <span className="checkerboard flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-line">
      {url ? (
        <img src={url} alt={alt} className="h-full w-full object-cover" />
      ) : loading ? (
        <Spinner />
      ) : (
        <ImageIcon className="h-5 w-5 text-faint" aria-hidden />
      )}
    </span>
  );
}

function SelectedImage({
  image,
  onClear,
  hint,
}: {
  image: ImageRecord;
  onClear: () => void;
  hint?: string;
}) {
  const kind = imageKindLabel((image.metadata as { image_type?: string })?.image_type);

  return (
    <div className="flex items-center gap-4 rounded-lg border border-line bg-elevated/50 p-3">
      <Thumbnail imageId={image.id} alt={image.original_filename} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-fg" title={image.original_filename}>
          {image.original_filename}
        </p>
        <p className="mt-0.5 text-xs text-muted">
          {image.width} × {image.height} px · {formatBytes(image.file_size_bytes)}
        </p>
        {(kind || hint) && (
          <div className="mt-1.5 flex flex-wrap gap-1.5">
            {kind && <Badge>{kind}</Badge>}
            {hint && <Badge tone="accent">{hint}</Badge>}
          </div>
        )}
      </div>
      <Button variant="secondary" size="sm" onClick={onClear}>
        Change
      </Button>
    </div>
  );
}

function Library({
  kind,
  suggestedLabel,
  onPick,
  onClose,
}: {
  kind?: ImageKind;
  suggestedLabel?: string;
  onPick: (image: ImageRecord) => void;
  onClose: () => void;
}) {
  const [filter, setFilter] = useState<"suggested" | "all">(kind ? "suggested" : "all");
  const [images, setImages] = useState<ImageRecord[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");

  const load = useCallback(
    async (offset: number) => {
      const page = await listImages({
        limit: PAGE_SIZE,
        offset,
        image_type: filter === "suggested" ? kind : undefined,
      });
      return page;
    },
    [filter, kind],
  );

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    load(0)
      .then((page) => {
        if (cancelled) return;
        setImages(page.items);
        setTotal(page.total);
      })
      .catch((exception) => {
        if (!cancelled) setError(errorMessage(exception, "Couldn't load your images."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [load]);

  const loadMore = async () => {
    setLoadingMore(true);
    try {
      const page = await load(images.length);
      setImages((current) => [...current, ...page.items]);
      setTotal(page.total);
    } catch (exception) {
      setError(errorMessage(exception, "Couldn't load more images."));
    } finally {
      setLoadingMore(false);
    }
  };

  const visible = query.trim()
    ? images.filter((image) =>
        image.original_filename.toLowerCase().includes(query.trim().toLowerCase()),
      )
    : images;

  return (
    <div className="animate-fade-up overflow-hidden rounded-lg border border-line">
      <div className="flex flex-wrap items-center gap-2 border-b border-line bg-elevated/50 p-2">
        {kind && (
          <SegmentedControl
            label="Which images to show"
            value={filter}
            onChange={setFilter}
            options={[
              { value: "suggested", label: suggestedLabel ?? "Suggested" },
              { value: "all", label: "All images" },
            ]}
          />
        )}
        <div className="relative min-w-[10rem] flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" aria-hidden />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by file name"
            aria-label="Search images by file name"
            className="h-9 pl-8"
          />
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close library">
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="max-h-80 overflow-y-auto">
        {loading && <SkeletonRows rows={4} />}
        {!loading && error && <ErrorState message={error} />}
        {!loading && !error && visible.length === 0 && (
          <EmptyState
            icon={<FolderOpen className="h-5 w-5" />}
            title={query ? "No matching images" : "No images here yet"}
            description={
              query
                ? "Try a different search."
                : filter === "suggested"
                  ? "Switch to “All images”, or upload a new one."
                  : "Upload an image to get started."
            }
          />
        )}
        {!loading && visible.length > 0 && (
          <ul className="divide-y divide-line">
            {visible.map((image) => {
              const kindLabel = imageKindLabel(
                (image.metadata as { image_type?: string })?.image_type,
              );
              return (
                <li key={image.id}>
                  <button
                    type="button"
                    onClick={() => onPick(image)}
                    className="flex w-full items-center gap-3 px-3 py-2.5 text-left transition-colors hover:bg-elevated/70"
                  >
                    <ImageIcon className="h-4 w-4 shrink-0 text-faint" aria-hidden />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-fg">{image.original_filename}</span>
                      <span className="block text-xs text-muted">
                        {image.width} × {image.height} · {formatBytes(image.file_size_bytes)}
                        {kindLabel && ` · ${kindLabel}`}
                      </span>
                    </span>
                    <span className="hidden shrink-0 text-xs text-faint sm:block">
                      {formatRelative(image.created_at)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
        {!loading && !query && images.length < total && (
          <div className="border-t border-line p-2 text-center">
            <Button variant="ghost" size="sm" loading={loadingMore} onClick={() => void loadMore()}>
              Load more ({total - images.length} remaining)
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Choose the image a tool works on: upload a new file or reuse one from
 * the account's library.
 */
export function ImagePicker({
  value,
  onChange,
  kind,
  suggestedLabel,
  uploadAs,
  selectedHint,
  allowPathRegistration = false,
  compact = false,
}: {
  value: ImageRecord | null;
  onChange: (image: ImageRecord | null) => void;
  /** Library filter suggested for this tool. */
  kind?: ImageKind;
  suggestedLabel?: string;
  /** How new uploads are labelled on the server. */
  uploadAs: ImageKind;
  selectedHint?: string;
  allowPathRegistration?: boolean;
  /** Shorter drop zone for dense forms. */
  compact?: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(false);
  const [pathOpen, setPathOpen] = useState(false);
  const [pathValue, setPathValue] = useState("");
  const [registering, setRegistering] = useState(false);

  const handleFile = async (file: File | undefined) => {
    if (!file) return;
    setUploadError(null);

    if (file.size > MAX_UPLOAD_BYTES) {
      setUploadError("That file is larger than 25 MB. Choose a smaller image.");
      return;
    }

    setUploading(true);
    try {
      onChange(await uploadImage(file, uploadAs));
      setLibraryOpen(false);
    } catch (exception) {
      setUploadError(errorMessage(exception, "The upload failed. Please try again."));
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void handleFile(event.dataTransfer.files?.[0]);
  };

  const handleRegisterPath = async () => {
    if (!pathValue.trim()) return;
    setRegistering(true);
    setUploadError(null);
    try {
      onChange(await registerImagePath(pathValue.trim(), uploadAs));
      setPathValue("");
      setPathOpen(false);
    } catch (exception) {
      setUploadError(errorMessage(exception, "That path couldn't be registered."));
    } finally {
      setRegistering(false);
    }
  };

  if (value) {
    return <SelectedImage image={value} onClear={() => onChange(null)} hint={selectedHint} />;
  }

  return (
    <div className="space-y-3">
      <div
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={cn(
          "flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 text-center transition-colors",
          compact ? "py-5" : "py-8",
          dragging ? "border-accent bg-accent-soft/60" : "border-line-strong bg-elevated/40",
        )}
      >
        {uploading ? (
          <>
            <Spinner className="h-6 w-6" />
            <p className="mt-3 text-sm font-medium text-fg">Uploading…</p>
          </>
        ) : (
          <>
            <span
              className={cn(
                "flex items-center justify-center rounded-full bg-surface text-accent shadow-sm",
                compact ? "h-9 w-9" : "h-11 w-11",
              )}
            >
              <Upload className="h-5 w-5" aria-hidden />
            </span>
            <p className={cn("text-sm font-medium text-fg", compact ? "mt-2" : "mt-3")}>
              Drag an image here, or{" "}
              <button
                type="button"
                onClick={() => inputRef.current?.click()}
                className="text-accent underline-offset-2 hover:underline"
              >
                browse your files
              </button>
            </p>
            <p className="mt-1 text-xs text-muted">PNG, JPG, BMP, TIFF, WebP, PGM or PPM · up to 25 MB</p>
          </>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label="Upload an image"
          onChange={(event) => void handleFile(event.target.files?.[0])}
        />
      </div>

      {uploadError && (
        <Callout tone="danger" role="alert">
          {uploadError}
        </Callout>
      )}

      {libraryOpen ? (
        <Library
          kind={kind}
          suggestedLabel={suggestedLabel}
          onPick={(image) => {
            onChange(image);
            setLibraryOpen(false);
          }}
          onClose={() => setLibraryOpen(false)}
        />
      ) : (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <Button variant="secondary" size="sm" onClick={() => setLibraryOpen(true)}>
            <FolderOpen className="h-4 w-4" aria-hidden />
            Choose from my images
          </Button>
          {allowPathRegistration && (
            <button
              type="button"
              onClick={() => setPathOpen((open) => !open)}
              aria-expanded={pathOpen}
              className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-fg"
            >
              <HardDriveDownload className="h-3.5 w-3.5" aria-hidden />
              Advanced: use a file already on the server
            </button>
          )}
        </div>
      )}

      {pathOpen && !libraryOpen && (
        <div className="animate-fade-up rounded-lg border border-line bg-elevated/40 p-3">
          <Field
            label="Server path"
            help="For research datasets already stored under the server's storage/ folder, e.g. BOSSBase images."
          >
            <Input
              value={pathValue}
              placeholder="storage/dataset/bossbase/clean/1127.pgm"
              onChange={(event) => setPathValue(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void handleRegisterPath();
              }}
              className="font-mono text-xs"
            />
          </Field>
          <Button
            variant="secondary"
            size="sm"
            className="mt-2"
            loading={registering}
            disabled={!pathValue.trim()}
            onClick={() => void handleRegisterPath()}
          >
            Use this file
          </Button>
        </div>
      )}
    </div>
  );
}
