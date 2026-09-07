import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type DragEvent,
} from "react";
import { FolderOpen, HardDriveDownload, Images, Upload } from "lucide-react";
import { ApiError } from "@/api/client";
import { listImages, registerImagePath, uploadImage } from "@/api/images";
import type { ImageRecord } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/lib/cn";
import { formatBytes, formatRelative } from "@/lib/format";
import { Button } from "./ui/Button";
import { Input, Label } from "./ui/Field";
import { EmptyState, ErrorState, SkeletonRows } from "./ui/States";

interface ImageSelectorProps {
  selectedId: string | null;
  onSelect: (image: ImageRecord) => void;
  imageType?: "COVER" | "SUSPECT" | "STEGO";
  /** Show the storage-path registration box (useful for dataset files). */
  allowPathRegistration?: boolean;
  className?: string;
}

export function ImageSelector({
  selectedId,
  onSelect,
  imageType = "COVER",
  allowPathRegistration = false,
  className,
}: ImageSelectorProps) {
  const { notify } = useToast();
  const inputRef = useRef<HTMLInputElement>(null);

  const [images, setImages] = useState<ImageRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [showPathBox, setShowPathBox] = useState(false);
  const [pathValue, setPathValue] = useState("");
  const [registering, setRegistering] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setLoadError(null);

    try {
      const page = await listImages({ limit: 60 });
      setImages(page.items);
    } catch (exception) {
      setLoadError(
        exception instanceof ApiError
          ? exception.message
          : "Unable to load your image library.",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0];
      if (!file) return;

      setUploading(true);

      try {
        const record = await uploadImage(file, imageType);
        setImages((current) => [
          record,
          ...current.filter((item) => item.id !== record.id),
        ]);
        onSelect(record);
        notify(`${record.original_filename} is ready to analyse.`, "success");
      } catch (exception) {
        notify(
          exception instanceof ApiError
            ? exception.message
            : "Image upload failed.",
          "error",
        );
      } finally {
        setUploading(false);
        if (inputRef.current) inputRef.current.value = "";
      }
    },
    [imageType, notify, onSelect],
  );

  const handleDrop = (event: DragEvent<HTMLDivElement>) => {
    event.preventDefault();
    setDragging(false);
    void handleFiles(event.dataTransfer.files);
  };

  const handleRegisterPath = async () => {
    if (!pathValue.trim()) return;

    setRegistering(true);

    try {
      const record = await registerImagePath(pathValue.trim(), imageType);
      setImages((current) => [
        record,
        ...current.filter((item) => item.id !== record.id),
      ]);
      onSelect(record);
      setPathValue("");
      setShowPathBox(false);
      notify(`Registered ${record.original_filename}.`, "success");
    } catch (exception) {
      notify(
        exception instanceof ApiError
          ? exception.message
          : "Could not register that path.",
        "error",
      );
    } finally {
      setRegistering(false);
    }
  };

  return (
    <div className={cn("flex h-full flex-col", className)}>
      <div className="p-5 pb-4">
        <div
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className={cn(
            "rounded-lg border-2 border-dashed p-6 text-center transition-colors",
            dragging ? "border-accent bg-accent-soft/50" : "border-line bg-elevated/40",
          )}
        >
          <Upload className="mx-auto h-5 w-5 text-faint" aria-hidden />
          <p className="mt-2 text-xs text-muted">
            Drop an image here, or
          </p>
          <Button
            size="sm"
            variant="secondary"
            className="mt-2"
            loading={uploading}
            onClick={() => inputRef.current?.click()}
          >
            Choose file
          </Button>
          <p className="mt-2 text-[11px] text-faint">
            PNG, JPG, BMP, TIFF, PGM or PPM · up to 25 MB
          </p>
          <input
            ref={inputRef}
            type="file"
            accept=".png,.jpg,.jpeg,.bmp,.tif,.tiff,.pgm,.ppm,.webp"
            className="sr-only"
            aria-label="Upload an image"
            onChange={(event) => void handleFiles(event.target.files)}
          />
        </div>

        {allowPathRegistration && (
          <div className="mt-3">
            <button
              type="button"
              onClick={() => setShowPathBox((value) => !value)}
              className="flex items-center gap-1.5 text-[11px] font-medium text-muted transition-colors hover:text-accent"
            >
              <HardDriveDownload className="h-3 w-3" />
              Register an existing storage path
            </button>

            {showPathBox && (
              <div className="mt-2 animate-fade-up rounded-lg border border-line bg-elevated/40 p-3">
                <Label htmlFor="storage-path" hint="must be inside storage/">
                  Storage path
                </Label>
                <div className="flex gap-2">
                  <Input
                    id="storage-path"
                    value={pathValue}
                    placeholder="storage/dataset/bossbase/clean/1127.pgm"
                    onChange={(event) => setPathValue(event.target.value)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") void handleRegisterPath();
                    }}
                    className="font-mono text-xs"
                  />
                  <Button
                    size="md"
                    variant="secondary"
                    loading={registering}
                    onClick={() => void handleRegisterPath()}
                  >
                    Add
                  </Button>
                </div>
                <p className="mt-1.5 text-[11px] leading-relaxed text-faint">
                  Useful for evaluating dataset files that are already on the
                  server, such as BOSSBase cover/stego pairs.
                </p>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-line px-5 py-2.5">
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted">
          <Images className="h-3.5 w-3.5" />
          Library
          {images.length > 0 && (
            <span className="text-faint">({images.length})</span>
          )}
        </span>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 px-2 text-[11px]"
          onClick={() => void refresh()}
        >
          Refresh
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && <SkeletonRows rows={4} />}

        {!loading && loadError && (
          <ErrorState message={loadError} onRetry={() => void refresh()} />
        )}

        {!loading && !loadError && images.length === 0 && (
          <EmptyState
            icon={<FolderOpen className="h-5 w-5" />}
            title="Your library is empty"
            description="Uploaded images are registered against your account and become available to every workspace."
          />
        )}

        {!loading && !loadError && images.length > 0 && (
          <ul className="divide-y divide-line">
            {images.map((image) => {
              const kind = String(
                (image.metadata as { image_type?: string })?.image_type ?? "",
              );

              return (
                <li key={image.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(image)}
                    aria-current={selectedId === image.id}
                    className={cn(
                      "flex w-full items-center gap-3 px-5 py-3 text-left transition-colors",
                      selectedId === image.id
                        ? "bg-accent-soft/60"
                        : "hover:bg-elevated/60",
                    )}
                  >
                    <span
                      className={cn(
                        "h-8 w-1 shrink-0 rounded-full",
                        selectedId === image.id ? "bg-accent" : "bg-line",
                      )}
                    />
                    <span className="min-w-0 flex-1">
                      <span
                        className="block truncate text-xs font-medium text-fg"
                        title={image.original_filename}
                      >
                        {image.original_filename}
                      </span>
                      <span className="mt-0.5 block font-mono text-[11px] text-faint">
                        {image.width}×{image.height} ·{" "}
                        {formatBytes(image.file_size_bytes)}
                        {kind && ` · ${kind}`}
                      </span>
                    </span>
                    <span className="shrink-0 text-[11px] text-faint">
                      {formatRelative(image.created_at)}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
