import { useState } from "react";
import { CheckCircle2, Download, KeyRound, RotateCcw, ScanSearch, TriangleAlert } from "lucide-react";
import { downloadImage } from "@/api/images";
import type { AdaptiveEmbedResult, EmbedResult, ImageRecord } from "@/api/types";
import { errorMessage } from "@/hooks/useAsync";
import { useToast } from "@/context/ToastContext";
import {
  CAPACITY_HELP,
  CHANGE_RATE_HELP,
  PSNR_HELP,
  SSIM_HELP,
  methodWithParams,
  psnrVerdict,
} from "@/lib/describe";
import { cn } from "@/lib/cn";
import { formatBytes, formatMs, formatNumber, formatPercent, shortId } from "@/lib/format";
import { Button, ButtonLink } from "@/components/ui/Button";
import { InfoTip } from "@/components/ui/InfoTip";
import { Stat } from "@/components/ui/Stat";
import { DetectionSummary, SelectionDetails } from "./SelectionDetails";
import { VisualComparison } from "./VisualComparison";

const TONE_TEXT = { clean: "text-clean", warn: "text-warn", stego: "text-stego" } as const;

export function isAdaptiveResult(
  result: EmbedResult | AdaptiveEmbedResult | null,
): result is AdaptiveEmbedResult {
  return result?.mode === "ADAPTIVE";
}

export function HideResult({
  result,
  cover,
  onReset,
}: {
  result: EmbedResult | AdaptiveEmbedResult;
  cover: ImageRecord;
  onReset: () => void;
}) {
  const { notify } = useToast();
  const [downloading, setDownloading] = useState(false);

  const adaptive = isAdaptiveResult(result) ? result : null;
  const verified = result.extraction_verified;
  const quality = psnrVerdict(result.psnr);
  const method = methodWithParams(result.method, result.channel_mode, result.lsb_bits);

  const download = async () => {
    setDownloading(true);
    try {
      await downloadImage(
        result.stego_image_id,
        `stegolab_${result.method.toLowerCase()}_${shortId(result.session_id)}.png`,
      );
    } catch (exception) {
      notify(errorMessage(exception, "The download failed."), "error");
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="space-y-6">
      <section
        className={cn(
          "rounded-xl border p-5 sm:p-6",
          verified ? "border-clean/30 bg-clean/5" : "border-warn/30 bg-warn/5",
        )}
        aria-live="polite"
      >
        <div className="flex flex-wrap items-start gap-4">
          <span
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-full",
              verified ? "bg-clean/15 text-clean" : "bg-warn/15 text-warn",
            )}
          >
            {verified ? <CheckCircle2 className="h-6 w-6" /> : <TriangleAlert className="h-6 w-6" />}
          </span>
          <div className="min-w-0 flex-1">
            <h2 className="text-lg font-semibold text-fg">
              {verified ? "Your message is hidden" : "The image was created, but the check failed"}
            </h2>
            <p className="mt-1 text-sm leading-relaxed text-muted">
              {verified
                ? "StegoLab read the message back from the new image and it matched exactly."
                : "Reading the message back didn't return the original text, so don't rely on this image. Try a shorter message or a different method."}{" "}
              {adaptive
                ? `Method chosen automatically: ${method}, the best of ${adaptive.candidates.length} options.`
                : `Method: ${method}.`}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button onClick={() => void download()} loading={downloading}>
                <Download className="h-4 w-4" aria-hidden />
                Download image
              </Button>
              <ButtonLink to={`/extract?image=${result.stego_image_id}`} variant="secondary">
                <KeyRound className="h-4 w-4" aria-hidden />
                Extract to check
              </ButtonLink>
              <ButtonLink to={`/analyze?image=${result.stego_image_id}`} variant="secondary">
                <ScanSearch className="h-4 w-4" aria-hidden />
                Analyze this image
              </ButtonLink>
              <Button variant="ghost" onClick={onReset}>
                <RotateCcw className="h-4 w-4" aria-hidden />
                Hide another message
              </Button>
            </div>
            <p className="mt-3 text-xs text-muted">
              Share the downloaded PNG as-is. Editing, resizing or re-saving it as
              JPEG will usually destroy the message.
            </p>
          </div>
        </div>
      </section>

      <VisualComparison
        coverId={cover.id}
        stegoId={result.stego_image_id}
        width={cover.width}
        height={cover.height}
        coverFormat={cover.mime_type || cover.file_extension}
      />

      <section aria-labelledby="measurements-heading">
        <h2 id="measurements-heading" className="mb-3 text-base font-semibold text-fg">
          Measurements
        </h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Stat
            label="Image quality"
            info={<InfoTip label="About PSNR">{PSNR_HELP}</InfoTip>}
            value={result.psnr === null ? "∞" : `${formatNumber(result.psnr, 1)} dB`}
            hint={<span className={TONE_TEXT[quality.tone]}>{quality.label}</span>}
          />
          <Stat
            label="Structural similarity"
            info={<InfoTip label="About SSIM">{SSIM_HELP}</InfoTip>}
            value={formatNumber(result.ssim, 5)}
            hint="1.0 = structurally identical"
          />
          {adaptive && adaptive.change_rate !== null ? (
            <Stat
              label="Colour values changed"
              info={<InfoTip label="About changed values">{CHANGE_RATE_HELP}</InfoTip>}
              value={formatPercent(adaptive.change_rate, 3)}
              hint="of all colour values in the image"
            />
          ) : (
            <Stat label="Mean squared error" value={formatNumber(result.mse, 5)} hint="Lower means less change" />
          )}
          <Stat
            label="Space used"
            info={<InfoTip label="About space used">{CAPACITY_HELP}</InfoTip>}
            value={formatPercent(result.capacity_used_ratio, 2)}
            hint={`${formatBytes(result.payload_size_bytes)} of ${formatBytes(result.capacity_bytes)}`}
          />
        </div>
        <p className="mt-2 text-xs text-muted">
          Finished in {formatMs(result.processing_time_ms)}
          {adaptive ? " (all options, excluding the saved report)" : ""}.
        </p>
      </section>

      {adaptive && (
        <>
          <SelectionDetails comparison={adaptive} />
          <DetectionSummary steganalysis={adaptive.steganalysis} />
        </>
      )}
    </div>
  );
}
