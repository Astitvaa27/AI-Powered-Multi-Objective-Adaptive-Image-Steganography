import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ArrowRightLeft,
  CheckCircle2,
  Gauge,
  HardDrive,
  Image as ImageIcon,
  KeyRound,
  Play,
  Radar,
  Settings2,
  ShieldHalf,
  Timer,
  XCircle,
} from "lucide-react";
import { ApiError } from "@/api/client";
import {
  embedPayload,
  extractPayload,
  getCapacity,
  listMethods,
} from "@/api/steganography";
import type {
  CapacityInfo,
  EmbedResult,
  EmbeddingMethodInfo,
  ExtractResult,
  ImageRecord,
} from "@/api/types";
import { AppLayout } from "@/components/layout/AppLayout";
import { ImagePreview } from "@/components/ImagePreview";
import { ImageSelector } from "@/components/ImageSelector";
import { MetricCard } from "@/components/MetricCard";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Label, Select, Textarea } from "@/components/ui/Field";
import { ProgressBar } from "@/components/ui/Progress";
import { EmptyState, ErrorState, LoadingState } from "@/components/ui/States";
import { useToast } from "@/context/ToastContext";
import { cn } from "@/lib/cn";
import { formatBytes, formatMs, formatNumber, formatPercent } from "@/lib/format";
import { Download } from "lucide-react";
import { downloadImage } from "@/api/images";

const EMBED_STEPS = [
  "Reading cover image",
  "Embedding payload",
  "Verifying extraction",
  "Measuring MSE / PSNR / SSIM",
];

type Mode = "embed" | "extract";

export function SteganographyPage() {
  const { notify } = useToast();

  const [mode, setMode] = useState<Mode>("embed");
  const [image, setImage] = useState<ImageRecord | null>(null);
  const [methods, setMethods] = useState<EmbeddingMethodInfo[]>([]);
  const [method, setMethod] = useState<"LSB" | "DCT" | "DWT">("LSB");
  const [channelMode, setChannelMode] = useState("RGB");
  const [lsbBits, setLsbBits] = useState(1);
  const [payload, setPayload] = useState("");

  const [capacity, setCapacity] = useState<CapacityInfo | null>(null);
  const [embedResult, setEmbedResult] = useState<EmbedResult | null>(null);
  const [extractResult, setExtractResult] = useState<ExtractResult | null>(null);

  const [busy, setBusy] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    listMethods()
      .then(setMethods)
      .catch(() => setMethods([]));
  }, []);

  useEffect(() => {
    if (!busy) return;

    setStepIndex(0);
    const timer = window.setInterval(() => {
      setStepIndex((current) =>
        current < EMBED_STEPS.length - 1 ? current + 1 : current,
      );
    }, 650);

    return () => window.clearInterval(timer);
  }, [busy]);

  // Capacity only applies to LSB, where the backend exposes it.
  const refreshCapacity = useCallback(async () => {
    if (!image || method !== "LSB") {
      setCapacity(null);
      return;
    }

    try {
      setCapacity(
        await getCapacity({
          image_id: image.id,
          channel_mode: channelMode,
          lsb_bits: lsbBits,
        }),
      );
    } catch {
      setCapacity(null);
    }
  }, [image, method, channelMode, lsbBits]);

  useEffect(() => {
    void refreshCapacity();
  }, [refreshCapacity]);

  const payloadBytes = new TextEncoder().encode(payload).length;
  const overCapacity = Boolean(
    capacity && payloadBytes > capacity.capacity_bytes,
  );

  const selectedMethod = methods.find((entry) => entry.code === method);
  const supportsChannel = selectedMethod?.supports.channel_mode ?? method === "LSB";
  const supportsBits = selectedMethod?.supports.lsb_bits ?? method === "LSB";

  const handleSelect = (selected: ImageRecord) => {
    setImage(selected);
    setEmbedResult(null);
    setExtractResult(null);
    setError(null);
  };

  const runEmbed = async () => {
    if (!image || !payload.trim()) return;

    setBusy(true);
    setError(null);
    setEmbedResult(null);

    try {
      const result = await embedPayload({
        cover_image_id: image.id,
        method,
        payload_text: payload,
        channel_mode: channelMode,
        lsb_bits: lsbBits,
      });

      setEmbedResult(result);
      notify(
        result.extraction_verified
          ? "Payload embedded and verified by extraction."
          : "Payload embedded, but extraction did not match.",
        result.extraction_verified ? "success" : "error",
      );
    } catch (exception) {
      const message =
        exception instanceof ApiError
          ? exception.message
          : "Embedding failed unexpectedly.";
      setError(message);
      notify(message, "error");
    } finally {
      setBusy(false);
    }
  };

  const runExtract = async () => {
    if (!image) return;

    setBusy(true);
    setError(null);
    setExtractResult(null);

    try {
      const result = await extractPayload({
        image_id: image.id,
        method,
        channel_mode: channelMode,
        lsb_bits: lsbBits,
      });

      setExtractResult(result);
      notify(
        result.is_probably_text
          ? "Payload recovered."
          : "Extraction completed, but the result does not look like text.",
        result.is_probably_text ? "success" : "info",
      );
    } catch (exception) {
      const message =
        exception instanceof ApiError
          ? exception.message
          : "Extraction failed unexpectedly.";
      setError(message);
      notify(message, "error");
    } finally {
      setBusy(false);
    }
  };

  const handleDownload = async () => {
  if (!embedResult) return;

  setDownloading(true);

  try {
    // The backend writes stego output as PNG named after the session.
    await downloadImage(
      embedResult.stego_image_id,
      `stego_${embedResult.method.toLowerCase()}_${embedResult.session_id}.png`,
    );
  } catch (exception) {
    notify(
      exception instanceof ApiError
        ? exception.message
        : "Download failed.",
      "error",
    );
  } finally {
    setDownloading(false);
  }
};

  return (
    <AppLayout
      title="Steganography"
      subtitle="Embed and recover payloads with measured image quality"
    >
      <div className="grid gap-6 xl:grid-cols-[22rem_minmax(0,1fr)] 2xl:grid-cols-[24rem_minmax(0,1fr)]">
        <div className="space-y-6">
          <Card className="flex max-h-[34rem] flex-col overflow-hidden">
            <CardHeader
              title={mode === "embed" ? "Cover image" : "Stego image"}
              description={
                mode === "embed"
                  ? "The image the payload will be hidden inside"
                  : "The image to recover a payload from"
              }
              icon={<ImageIcon className="h-4 w-4" />}
            />
            <ImageSelector
              selectedId={image?.id ?? null}
              onSelect={handleSelect}
              imageType={mode === "embed" ? "COVER" : "STEGO"}
              allowPathRegistration
              className="min-h-0 flex-1"
            />
          </Card>

          <Card>
            <CardHeader
              title="Configuration"
              description="Only backend-supported controls are shown"
              icon={<Settings2 className="h-4 w-4" />}
            />
            <CardBody className="space-y-4">
              <div
                className="grid grid-cols-2 gap-1 rounded-lg bg-elevated p-1"
                role="tablist"
              >
                {(["embed", "extract"] as const).map((value) => (
                  <button
                    key={value}
                    type="button"
                    role="tab"
                    aria-selected={mode === value}
                    onClick={() => {
                      setMode(value);
                      setError(null);
                    }}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-xs font-medium capitalize transition-colors",
                      mode === value
                        ? "bg-surface text-fg shadow-sm"
                        : "text-muted hover:text-fg",
                    )}
                  >
                    {value}
                  </button>
                ))}
              </div>

              <div>
                <Label htmlFor="method">Embedding method</Label>
                <Select
                  id="method"
                  value={method}
                  onChange={(event) =>
                    setMethod(event.target.value as "LSB" | "DCT" | "DWT")
                  }
                >
                  <option value="LSB">LSB — least significant bit</option>
                  <option value="DCT">DCT — discrete cosine transform</option>
                  <option value="DWT">DWT — Haar wavelet</option>
                </Select>
                {selectedMethod && !selectedMethod.registered && (
                  <p className="mt-1.5 text-[11px] text-warn">
                    This method is implemented but not registered as active in
                    the database.
                  </p>
                )}
              </div>

              {supportsChannel && (
                <div>
                  <Label htmlFor="channel">Channel mode</Label>
                  <Select
                    id="channel"
                    value={channelMode}
                    onChange={(event) => setChannelMode(event.target.value)}
                  >
                    <option value="RGB">RGB — all channels</option>
                    <option value="R">R — red only</option>
                    <option value="G">G — green only</option>
                    <option value="B">B — blue only</option>
                  </Select>
                </div>
              )}

              {supportsBits && (
                <div>
                  <Label htmlFor="bits" hint="1 – 3">
                    LSB bits per channel
                  </Label>
                  <Select
                    id="bits"
                    value={lsbBits}
                    onChange={(event) => setLsbBits(Number(event.target.value))}
                  >
                    <option value={1}>1 bit — lowest distortion</option>
                    <option value={2}>2 bits</option>
                    <option value={3}>3 bits — highest capacity</option>
                  </Select>
                </div>
              )}

              {!supportsChannel && !supportsBits && (
                <p className="rounded-lg border border-line bg-elevated/40 px-3 py-2 text-[11px] leading-relaxed text-muted">
                  {method} embedding operates on the blue channel with fixed
                  parameters in this implementation, so no additional controls
                  apply.
                </p>
              )}

              {mode === "embed" && (
                <div>
                  <Label
                    htmlFor="payload"
                    hint={`${payloadBytes} bytes`}
                  >
                    Payload text
                  </Label>
                  <Textarea
                    id="payload"
                    rows={5}
                    value={payload}
                    onChange={(event) => setPayload(event.target.value)}
                    placeholder="Type the message to hide inside the cover image…"
                  />

                  {capacity && (
                    <div className="mt-2">
                      <div className="mb-1 flex items-baseline justify-between text-[11px]">
                        <span className="text-muted">Capacity used</span>
                        <span
                          className={cn(
                            "font-mono tabular-nums",
                            overCapacity ? "text-stego" : "text-muted",
                          )}
                        >
                          {formatBytes(payloadBytes)} /{" "}
                          {formatBytes(capacity.capacity_bytes)}
                        </span>
                      </div>
                      <ProgressBar
                        value={payloadBytes / capacity.capacity_bytes}
                        tone={overCapacity ? "stego" : "accent"}
                        label="Payload capacity usage"
                      />
                      {overCapacity && (
                        <p className="mt-1.5 text-[11px] text-stego">
                          Payload exceeds the available capacity for this
                          configuration.
                        </p>
                      )}
                    </div>
                  )}
                </div>
              )}

              <Button
                className="w-full"
                size="lg"
                loading={busy}
                disabled={
                  !image ||
                  (mode === "embed" && (!payload.trim() || overCapacity))
                }
                onClick={() =>
                  void (mode === "embed" ? runEmbed() : runExtract())
                }
              >
                {mode === "embed" ? (
                  <>
                    <Play className="h-4 w-4" />
                    Embed payload
                  </>
                ) : (
                  <>
                    <KeyRound className="h-4 w-4" />
                    Extract payload
                  </>
                )}
              </Button>
            </CardBody>
          </Card>
        </div>

        <div className="min-w-0 space-y-6">
          <div className="grid gap-6 2xl:grid-cols-2">
            <Card>
              <CardHeader
                title={mode === "embed" ? "Cover image" : "Source image"}
                icon={<ImageIcon className="h-4 w-4" />}
              />
              <CardBody>
                <ImagePreview
                  imageId={image?.id ?? null}
                  meta={image}
                  minHeightClass="min-h-[20rem]"
                />
              </CardBody>
            </Card>

            <Card>
              <CardHeader
                title="Stego output"
                description={
                  embedResult
                    ? "Produced by the embedding run"
                    : "Appears once a payload is embedded"
                }
                icon={<ShieldHalf className="h-4 w-4" />}
                actions={
  embedResult && (
    <>
      <Button
        variant="secondary"
        size="sm"
        loading={downloading}
        onClick={() => void handleDownload()}
      >
        <Download className="h-3.5 w-3.5" />
        Download
      </Button>
      <Link to="/steganalysis">
        <Button variant="secondary" size="sm">
          <Radar className="h-3.5 w-3.5" />
          Analyse
        </Button>
      </Link>
    </>
  )
}
              />
              <CardBody>
                {embedResult ? (
                  <ImagePreview
                    imageId={embedResult.stego_image_id}
                    minHeightClass="min-h-[20rem]"
                  />
                ) : (
                  <EmptyState
                    icon={<HardDrive className="h-5 w-5" />}
                    title="No stego image yet"
                    description="The generated image is registered to your library and can be sent straight to steganalysis."
                    className="min-h-[20rem]"
                  />
                )}
              </CardBody>
            </Card>
          </div>

          {busy && (
            <Card>
              <LoadingState
                label={mode === "embed" ? "Embedding payload…" : "Extracting payload…"}
                steps={mode === "embed" ? EMBED_STEPS : undefined}
                activeStep={stepIndex}
              />
            </Card>
          )}

          {error && !busy && (
            <Card>
              <ErrorState title="Operation failed" message={error} />
            </Card>
          )}

          {embedResult && mode === "embed" && !busy && (
            <>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                <MetricCard
                  label="PSNR"
                  value={
                    embedResult.psnr === null
                      ? "∞"
                      : `${formatNumber(embedResult.psnr, 2)}`
                  }
                  hint="dB — higher is less perceptible"
                  tone="accent"
                  icon={<Gauge className="h-4 w-4" />}
                />
                <MetricCard
                  label="SSIM"
                  value={formatNumber(embedResult.ssim, 5)}
                  hint="1.0 is identical structure"
                  tone="accent"
                />
                <MetricCard
                  label="MSE"
                  value={formatNumber(embedResult.mse, 5)}
                  hint="Lower is less distortion"
                />
                <MetricCard
                  label="Processing time"
                  value={formatMs(embedResult.processing_time_ms)}
                  icon={<Timer className="h-4 w-4" />}
                />
              </div>

              <Card>
                <CardHeader
                  title="Embedding summary"
                  icon={<ArrowRightLeft className="h-4 w-4" />}
                  actions={
                    <Badge
                      tone={embedResult.extraction_verified ? "clean" : "stego"}
                    >
                      {embedResult.extraction_verified
                        ? "Extraction verified"
                        : "Verification failed"}
                    </Badge>
                  }
                />
                <CardBody className="grid gap-6 lg:grid-cols-2">
                  <dl className="space-y-2.5 text-xs">
                    <SummaryRow label="Method" value={embedResult.method} />
                    {embedResult.channel_mode && (
                      <SummaryRow
                        label="Channel mode"
                        value={embedResult.channel_mode}
                      />
                    )}
                    {embedResult.lsb_bits !== null && (
                      <SummaryRow
                        label="LSB bits"
                        value={String(embedResult.lsb_bits)}
                      />
                    )}
                    <SummaryRow
                      label="Payload size"
                      value={formatBytes(embedResult.payload_size_bytes)}
                    />
                    <SummaryRow
                      label="Capacity"
                      value={formatBytes(embedResult.capacity_bytes)}
                    />
                    <SummaryRow
                      label="Capacity used"
                      value={formatPercent(embedResult.capacity_used_ratio, 3)}
                    />
                    <SummaryRow
                      label="Output path"
                      value={embedResult.output_path}
                      mono
                    />
                  </dl>

                  <div className="rounded-lg border border-line bg-elevated/40 p-4">
                    <p className="flex items-center gap-1.5 text-xs font-medium text-fg">
                      {embedResult.extraction_verified ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-clean" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-stego" />
                      )}
                      Round-trip verification
                    </p>
                    <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
                      {embedResult.extraction_verified
                        ? "The payload was re-extracted from the stego image and matched the original byte-for-byte."
                        : "The re-extracted payload did not match the original. Try a lower bit depth or a smaller payload."}
                    </p>

                    {embedResult.extracted_preview && (
                      <pre className="mt-3 max-h-40 overflow-auto rounded border border-line bg-bg p-3 font-mono text-[11px] leading-relaxed text-fg">
                        {embedResult.extracted_preview}
                      </pre>
                    )}
                  </div>
                </CardBody>
              </Card>
            </>
          )}

          {extractResult && mode === "extract" && !busy && (
            <Card>
              <CardHeader
                title="Recovered payload"
                description={`${formatBytes(
                  extractResult.payload_size_bytes,
                )} recovered in ${formatMs(extractResult.processing_time_ms)}`}
                icon={<KeyRound className="h-4 w-4" />}
                actions={
                  <Badge tone={extractResult.is_probably_text ? "clean" : "warn"}>
                    {extractResult.is_probably_text
                      ? "Decoded as text"
                      : "Not valid UTF-8"}
                  </Badge>
                }
              />
              <CardBody>
                {!extractResult.is_probably_text && (
                  <p className="mb-3 rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-[11px] leading-relaxed text-fg">
                    The extracted bytes did not decode cleanly as text. The
                    image may not contain a payload embedded with these
                    settings, or a different method or bit depth was used.
                  </p>
                )}
                <pre className="max-h-72 overflow-auto rounded-lg border border-line bg-elevated/40 p-4 font-mono text-xs leading-relaxed text-fg">
                  {extractResult.payload_text || "(empty)"}
                </pre>
              </CardBody>
            </Card>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function SummaryRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="shrink-0 text-faint">{label}</dt>
      <dd
        className={cn(
          "truncate text-right font-medium text-fg",
          mono && "font-mono text-[11px]",
        )}
        title={value}
      >
        {value}
      </dd>
    </div>
  );
}
