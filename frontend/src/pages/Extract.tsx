import { useEffect, useRef, useState } from "react";
import { RotateCcw, ScanSearch, Square } from "lucide-react";
import { autoExtract } from "@/api/steganography";
import type { AutoExtractResult, ImageRecord } from "@/api/types";
import { errorMessage } from "@/hooks/useAsync";
import { useImageFromQuery } from "@/hooks/useImageFromQuery";
import { methodWithParams } from "@/lib/describe";
import { AppLayout } from "@/components/layout/AppLayout";
import { AutoExtractResultView } from "@/components/extract/AutoExtractResultView";
import {
  DetectionProgress,
  applyStageEvent,
  initialStages,
  type StageMap,
} from "@/components/extract/DetectionProgress";
import { ManualExtractPanel } from "@/components/extract/ManualExtractPanel";
import { ImagePicker } from "@/components/images/ImagePicker";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { Collapsible } from "@/components/ui/Collapsible";

/** Embedding details the backend stored on the image, if any. */
function recordedMethod(image: ImageRecord | null) {
  const metadata = (image?.metadata ?? {}) as {
    embedding_method?: string;
    embedding_mode?: string;
    channel_mode?: string;
    lsb_bits?: number;
  };
  if (!metadata.embedding_method) return null;
  return {
    label: methodWithParams(metadata.embedding_method, metadata.channel_mode, metadata.lsb_bits),
    adaptive: metadata.embedding_mode === "ADAPTIVE",
  };
}

export function ExtractPage() {
  const [image, setImage] = useState<ImageRecord | null>(null);
  const [runSteganalysis, setRunSteganalysis] = useState(true);

  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<StageMap>(initialStages);
  const [error, setError] = useState<string | null>(null);
  const [imageError, setImageError] = useState<string | null>(null);
  const [result, setResult] = useState<AutoExtractResult | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadingImage = useImageFromQuery(setImage);
  const recorded = recordedMethod(image);

  // Stop an in-flight detection when leaving the page.
  useEffect(() => () => abortRef.current?.abort(), []);

  const selectImage = (next: ImageRecord | null) => {
    abortRef.current?.abort();
    setImage(next);
    setResult(null);
    setError(null);
    setImageError(null);
  };

  const detect = async () => {
    if (running) return;
    if (!image) {
      setImageError("Choose or upload the image you want to check.");
      return;
    }

    const controller = new AbortController();
    abortRef.current = controller;
    setRunning(true);
    setError(null);
    setResult(null);
    setStages(initialStages());

    try {
      const outcome = await autoExtract(
        { image_id: image.id, run_steganalysis: runSteganalysis },
        (event) => setStages((current) => applyStageEvent(current, event)),
        controller.signal,
      );
      setResult(outcome);
    } catch (exception) {
      if (exception instanceof DOMException && exception.name === "AbortError") return;
      setError(errorMessage(exception, "Detection failed unexpectedly."));
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setRunning(false);
      }
    }
  };

  const cancel = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
  };

  return (
    <AppLayout
      title="Extract a Message"
      description="Find and read a hidden message — StegoLab works out how it was hidden for you."
    >
      <div className="mx-auto max-w-3xl space-y-4">
        <Card className="p-5 sm:p-6">
          <h2 className="text-base font-semibold text-fg">Choose the image</h2>
          <p className="mt-0.5 text-sm text-muted">
            Use an image made with StegoLab, or upload one from another app or website. Use the original
            file — screenshots and re-saved copies usually lose hidden data.
          </p>
          <div className="mt-4">
            {loadingImage ? (
              <p className="text-sm text-muted">Loading image…</p>
            ) : (
              <ImagePicker
                value={image}
                onChange={selectImage}
                kind="STEGO"
                suggestedLabel="With a hidden message"
                uploadAs="STEGO"
                allowPathRegistration
              />
            )}
            {imageError && <p className="mt-2 text-xs text-stego" role="alert">{imageError}</p>}
          </div>

          {image && (
            <div className="mt-4 space-y-3">
              {recorded ? (
                <Callout tone="info" title="StegoLab has a record of this image">
                  It was created with {recorded.label}
                  {recorded.adaptive ? " (chosen automatically)" : ""}. Those settings are tried first and
                  the result is checked against the message StegoLab stored.
                </Callout>
              ) : (
                <p className="text-sm text-muted">
                  No settings needed. StegoLab checks its records, known file formats and a range of
                  pixel-bit settings, then validates anything it finds.
                </p>
              )}
              <label className="flex cursor-pointer items-center gap-2 text-sm text-muted">
                <input
                  type="checkbox"
                  checked={runSteganalysis}
                  onChange={(event) => setRunSteganalysis(event.target.checked)}
                  className="h-4 w-4 accent-[rgb(var(--accent))]"
                  disabled={running}
                />
                Also run steganalysis (a statistical hint only; it never decides the result)
              </label>
            </div>
          )}

          <div className="mt-5 flex flex-wrap justify-end gap-2">
            {running ? (
              <Button variant="secondary" size="lg" onClick={cancel} className="w-full sm:w-auto">
                <Square className="h-4 w-4" aria-hidden />
                Cancel
              </Button>
            ) : (
              <Button size="lg" onClick={() => void detect()} className="w-full sm:w-auto">
                <ScanSearch className="h-4 w-4" aria-hidden />
                Detect and extract
              </Button>
            )}
          </div>
        </Card>

        {running && (
          <Card>
            <DetectionProgress stages={stages} />
          </Card>
        )}

        {error && !running && (
          <Callout tone="danger" role="alert" title="Detection could not run">
            {error}
          </Callout>
        )}

        {result && !running && (
          <>
            <AutoExtractResultView result={result} />
            <div className="flex justify-end">
              <Button variant="ghost" size="sm" onClick={() => selectImage(null)}>
                <RotateCcw className="h-3.5 w-3.5" aria-hidden />
                Check another image
              </Button>
            </div>
          </>
        )}

        {image && (
          <Card className="overflow-hidden">
            <Collapsible
              title="Manual extraction (advanced)"
              description="Choose the method and settings yourself, if you know exactly how the message was hidden."
              defaultOpen={false}
            >
              <ManualExtractPanel key={image.id} image={image} />
            </Collapsible>
          </Card>
        )}

        <p className="text-center text-xs text-muted">
          StegoLab messages aren&apos;t password-protected: anyone with the image and StegoLab can read
          them. StegoLab cannot read messages that another tool encrypted with a password.
        </p>
      </div>
    </AppLayout>
  );
}
