import { useState } from "react";
import { CheckCircle2, Download, KeyRound, TriangleAlert } from "lucide-react";
import { extractPayload } from "@/api/steganography";
import type { ExtractResult, ImageRecord } from "@/api/types";
import { errorMessage } from "@/hooks/useAsync";
import { METHOD_INFO, methodWithParams, type MethodCode } from "@/lib/describe";
import { formatBytes, formatMs } from "@/lib/format";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Collapsible } from "@/components/ui/Collapsible";
import { CopyButton } from "@/components/ui/CopyButton";
import { Field, Select } from "@/components/ui/Field";
import { Spinner } from "@/components/ui/States";

function downloadText(text: string, filename: string) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

/**
 * Manual extraction with an explicitly chosen method — the fallback when
 * the user knows exactly how the message was hidden. Uses the original
 * POST /steganography/extract endpoint unchanged.
 */
export function ManualExtractPanel({ image }: { image: ImageRecord }) {
  const [method, setMethod] = useState<MethodCode>("LSB");
  const [channelMode, setChannelMode] = useState("RGB");
  const [lsbBits, setLsbBits] = useState(1);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractResult | null>(null);

  const submit = async () => {
    if (running) return;
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      setResult(
        await extractPayload({
          image_id: image.id,
          method,
          channel_mode: channelMode,
          lsb_bits: lsbBits,
        }),
      );
    } catch (exception) {
      setError(errorMessage(exception, "Extraction failed unexpectedly."));
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-xs leading-relaxed text-muted">
        Only use this if you know exactly which StegoLab method and settings were used. Unlike automatic
        detection, the output here is not validated: a wrong choice simply returns unreadable bytes.
      </p>
      <div className="grid gap-4 rounded-lg border border-line bg-elevated/40 p-4 sm:grid-cols-3">
        <Field label="Method" help={METHOD_INFO[method].short + " · must match how it was hidden"} className="sm:col-span-3">
          <Select value={method} onChange={(event) => setMethod(event.target.value as MethodCode)}>
            {(Object.keys(METHOD_INFO) as MethodCode[]).map((code) => (
              <option key={code} value={code}>
                {METHOD_INFO[code].name}
              </option>
            ))}
          </Select>
        </Field>
        {method === "LSB" && (
          <>
            <Field label="Colour channels" className="sm:col-span-2">
              <Select value={channelMode} onChange={(event) => setChannelMode(event.target.value)}>
                <option value="RGB">All colours</option>
                <option value="R">Red only</option>
                <option value="G">Green only</option>
                <option value="B">Blue only</option>
              </Select>
            </Field>
            <Field label="Bits per value">
              <Select value={lsbBits} onChange={(event) => setLsbBits(Number(event.target.value))}>
                <option value={1}>1 bit</option>
                <option value={2}>2 bits</option>
                <option value={3}>3 bits</option>
              </Select>
            </Field>
          </>
        )}
      </div>
      <div className="flex justify-end">
        <Button variant="secondary" onClick={() => void submit()} disabled={running}>
          {running ? <Spinner /> : <KeyRound className="h-4 w-4" aria-hidden />}
          Extract with these settings
        </Button>
      </div>

      {error && !running && (
        <Callout tone="danger" role="alert" title="Nothing could be extracted">
          {error}
          <span className="mt-1 block">
            The image may not contain a message with these settings, may have been edited or re-saved, or a
            different method was used.
          </span>
        </Callout>
      )}

      {result && !running && (
        <div className="space-y-3 rounded-lg border border-line p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="flex items-start gap-2">
              {result.is_probably_text ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 text-clean" aria-hidden />
              ) : (
                <TriangleAlert className="mt-0.5 h-4 w-4 text-warn" aria-hidden />
              )}
              <div>
                <p className="text-sm font-medium text-fg">
                  {result.is_probably_text ? "Readable output" : "This doesn't look like a message"}
                </p>
                <p className="text-xs text-muted">
                  {formatBytes(result.payload_size_bytes)} read with{" "}
                  {methodWithParams(result.method, result.channel_mode, result.lsb_bits)} in{" "}
                  {formatMs(result.processing_time_ms)} · not validated
                </p>
              </div>
            </div>
            {result.is_probably_text && (
              <div className="flex gap-2">
                <CopyButton text={result.payload_text} />
                <Button variant="secondary" size="sm" onClick={() => downloadText(result.payload_text, "stegolab-message.txt")}>
                  <Download className="h-3.5 w-3.5" aria-hidden />
                  Save as .txt
                </Button>
              </div>
            )}
          </div>
          {result.is_probably_text ? (
            <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-elevated/50 p-4 font-mono text-sm leading-relaxed text-fg">
              {result.payload_text || "(empty message)"}
            </pre>
          ) : (
            <Collapsible title="Show the raw output anyway" className="rounded-lg border border-line">
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-all font-mono text-xs text-muted">
                {result.payload_text}
              </pre>
            </Collapsible>
          )}
        </div>
      )}
    </div>
  );
}
