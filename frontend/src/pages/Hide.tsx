import { useEffect, useState, type ReactNode } from "react";
import { LockKeyhole } from "lucide-react";
import { adaptiveEmbed, embedPayload, getCapacity } from "@/api/steganography";
import type { AdaptiveEmbedResult, EmbedResult, ImageRecord } from "@/api/types";
import { useToast } from "@/context/ToastContext";
import { errorMessage } from "@/hooks/useAsync";
import { useImageFromQuery } from "@/hooks/useImageFromQuery";
import { AppLayout } from "@/components/layout/AppLayout";
import { ImagePicker } from "@/components/images/ImagePicker";
import { HideResult } from "@/components/hide/HideResult";
import { MessageInput } from "@/components/hide/MessageInput";
import { HIDE_PRESETS, type PresetId } from "@/components/hide/presets";
import { StrategyPicker, type ManualSettings, type Strategy } from "@/components/hide/StrategyPicker";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card } from "@/components/ui/Card";
import { WorkingState } from "@/components/ui/States";

const AUTO_STAGES = [
  "Checking which methods have room for your message",
  "Hiding the message with each method",
  "Reading each message back to make sure nothing was lost",
  "Measuring image quality and how many values changed",
  "Testing whether the message survives JPEG re-saving",
  "Running the detector on each result",
  "Scoring every option and keeping the best one",
];

/** Compact numbered section inside a card. */
function Section({
  number,
  title,
  description,
  children,
}: {
  number: number;
  title: string;
  description?: string;
  children: ReactNode;
}) {
  return (
    <section className="p-4 sm:p-5">
      <div className="mb-3 flex items-baseline gap-2.5">
        <span
          className="flex h-6 w-6 shrink-0 translate-y-px items-center justify-center self-start rounded-full bg-accent-soft text-xs font-semibold text-accent"
          aria-hidden
        >
          {number}
        </span>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-fg">
            <span className="sr-only">Step {number}: </span>
            {title}
          </h2>
          {description && <p className="text-xs leading-relaxed text-muted">{description}</p>}
        </div>
      </div>
      {children}
    </section>
  );
}

export function HidePage() {
  const { notify } = useToast();

  const [image, setImage] = useState<ImageRecord | null>(null);
  const [message, setMessage] = useState("");
  const [strategy, setStrategy] = useState<Strategy>("auto");
  const [preset, setPreset] = useState<PresetId>("balanced");
  const [saveReport, setSaveReport] = useState(true);
  const [manual, setManual] = useState<ManualSettings>({ method: "LSB", channelMode: "RGB", lsbBits: 1 });
  const [capacity, setCapacity] = useState<number | null>(null);

  const [errors, setErrors] = useState<{ image?: string; message?: string }>({});
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<{ data: EmbedResult | AdaptiveEmbedResult; cover: ImageRecord } | null>(null);

  const loadingImage = useImageFromQuery(setImage);

  // The backend reports capacity up front only for manual LSB.
  useEffect(() => {
    setCapacity(null);
    if (!image || strategy !== "manual" || manual.method !== "LSB") return;

    let cancelled = false;
    getCapacity({ image_id: image.id, channel_mode: manual.channelMode, lsb_bits: manual.lsbBits })
      .then((info) => {
        if (!cancelled) setCapacity(info.capacity_bytes);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [image, strategy, manual.method, manual.channelMode, manual.lsbBits]);

  const messageBytes = new TextEncoder().encode(message).length;

  const submit = async () => {
    if (running) return;

    const nextErrors: typeof errors = {};
    if (!image) nextErrors.image = "Choose the image that will carry your message.";
    if (!message.trim()) nextErrors.message = "Write the message you want to hide.";
    setErrors(nextErrors);
    if (!image || nextErrors.message) return;
    if (capacity !== null && messageBytes > capacity) return;

    setRunning(true);
    setSubmitError(null);

    try {
      const data =
        strategy === "auto"
          ? await adaptiveEmbed({
              cover_image_id: image.id,
              payload_text: message,
              weights: HIDE_PRESETS.find((option) => option.id === preset)?.weights,
              run_steganalysis: saveReport,
            })
          : await embedPayload({
              cover_image_id: image.id,
              method: manual.method,
              payload_text: message,
              channel_mode: manual.channelMode,
              lsb_bits: manual.lsbBits,
            });

      setResult({ data, cover: image });
      notify(
        data.extraction_verified ? "Message hidden and verified." : "Image created, but verification failed.",
        data.extraction_verified ? "success" : "error",
      );
    } catch (exception) {
      setSubmitError(errorMessage(exception, "Hiding the message failed unexpectedly."));
    } finally {
      setRunning(false);
    }
  };

  const reset = () => {
    setResult(null);
    setMessage("");
    setImage(null);
    setSubmitError(null);
  };

  if (result) {
    return (
      <AppLayout title="Hide a Message" description="Here's your result.">
        <HideResult result={result.data} cover={result.cover} onReset={reset} />
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title="Hide a Message"
      description="Conceal a text message inside an image so that it looks unchanged."
    >
      {/* min-w-0 overrides the fieldset default of min-width: min-content,
          which otherwise stops the form shrinking on narrow screens. */}
      <fieldset
        disabled={running}
        className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)] lg:gap-5"
      >
        <legend className="sr-only">Hide a message</legend>

        {/* What to hide */}
        <Card className="min-w-0 divide-y divide-line">
          <Section
            number={1}
            title="Choose an image"
            description="Larger, detailed images have more room for a message."
          >
            {loadingImage ? (
              <p className="text-sm text-muted">Loading image…</p>
            ) : (
              <ImagePicker
                value={image}
                onChange={(next) => {
                  setImage(next);
                  setErrors((current) => ({ ...current, image: undefined }));
                }}
                kind="COVER"
                suggestedLabel="Originals"
                uploadAs="COVER"
                allowPathRegistration
                compact
              />
            )}
            {errors.image && (
              <p className="mt-2 text-xs text-stego" role="alert">
                {errors.image}
              </p>
            )}
          </Section>

          <Section number={2} title="Write your message">
            <MessageInput
              value={message}
              onChange={(next) => {
                setMessage(next);
                setErrors((current) => ({ ...current, message: undefined }));
              }}
              error={errors.message}
              capacityBytes={capacity}
            />
          </Section>
        </Card>

        {/* How to hide it + the primary action. Sticky on wide screens so the
            button stays in reach while the left column scrolls. */}
        <Card className="min-w-0 lg:sticky lg:top-4">
          <Section number={3} title="Choose how to hide it">
            <StrategyPicker
              strategy={strategy}
              onStrategyChange={setStrategy}
              preset={preset}
              onPresetChange={setPreset}
              manual={manual}
              onManualChange={setManual}
              saveReport={saveReport}
              onSaveReportChange={setSaveReport}
            />
          </Section>

          <div className="border-t border-line">
            {running ? (
              <WorkingState
                className="px-4 py-5 sm:px-5"
                title={strategy === "auto" ? "Finding the best way to hide your message…" : "Hiding your message…"}
                description={
                  strategy === "auto"
                    ? "Usually 5–30 seconds, longer for very large images. Please keep this page open."
                    : "This usually takes a few seconds."
                }
                stages={strategy === "auto" ? AUTO_STAGES : undefined}
              />
            ) : (
              <div className="space-y-3 p-4 sm:px-5">
                {submitError && (
                  <Callout tone="danger" role="alert" title="The message couldn't be hidden">
                    {submitError}
                    <span className="mt-1 block">
                      Try a shorter message, a larger image, or a different method.
                    </span>
                  </Callout>
                )}
                <Button size="lg" onClick={() => void submit()} className="w-full">
                  <LockKeyhole className="h-4 w-4" aria-hidden />
                  Hide message
                </Button>
                <p className="text-center text-xs text-muted">
                  {strategy === "auto"
                    ? "Your original image is kept; a new image is created."
                    : "Only the method you picked will be used."}
                </p>
              </div>
            )}
          </div>
        </Card>
      </fieldset>
    </AppLayout>
  );
}
