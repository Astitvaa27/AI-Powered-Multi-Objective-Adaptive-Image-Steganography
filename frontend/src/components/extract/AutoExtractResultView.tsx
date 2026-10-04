import { useState } from "react";
import {
  CheckCircle2,
  Download,
  FileSearch,
  KeyRound,
  ListChecks,
  ShieldCheck,
  TriangleAlert,
  XCircle,
} from "lucide-react";
import type {
  AutoCandidate,
  AutoExtractResult,
  AutoMethodTested,
  AutoValidation,
} from "@/api/types";
import { cn } from "@/lib/cn";
import { formatBytes, formatMs, formatPercent } from "@/lib/format";
import { Badge, type Tone } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Collapsible } from "@/components/ui/Collapsible";
import { CopyButton } from "@/components/ui/CopyButton";

const VALIDATION_UI: Record<AutoValidation, { label: string; tone: Tone; help: string }> = {
  VERIFIED: {
    label: "Verified",
    tone: "clean",
    help: "An integrity check (stored message hash or checksum) confirmed these exact bytes.",
  },
  PLAUSIBLE: {
    label: "Plausible · no checksum",
    tone: "accent",
    help: "The format's structure is valid and the content is readable, but the format has no checksum.",
  },
  UNVERIFIED: {
    label: "Unverified",
    tone: "warn",
    help: "Something was recovered, but the evidence is too weak to call it a hidden message.",
  },
};

export function ValidationBadge({ validation }: { validation: AutoValidation }) {
  const ui = VALIDATION_UI[validation];
  return (
    <Badge tone={ui.tone} title={ui.help}>
      {validation === "VERIFIED" && <ShieldCheck className="h-3 w-3" aria-hidden />}
      {ui.label}
    </Badge>
  );
}

const FAMILY_LABEL: Record<AutoCandidate["family"], string> = {
  STEGOLAB: "StegoLab format",
  EXTERNAL: "External tool format",
  GENERIC: "Generic technique",
};

const EXTENSIONS: Record<string, string> = {
  "PNG image": "png",
  "JPEG image": "jpg",
  "GIF image": "gif",
  "PDF document": "pdf",
  "ZIP archive": "zip",
  "gzip-compressed data": "gz",
  "7-Zip archive": "7z",
  "RAR archive": "rar",
  "MP3 audio": "mp3",
  "Ogg media": "ogg",
};

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

/** Save the recovered payload. Never opened or rendered by the app. */
function downloadPayload(candidate: AutoCandidate) {
  const { payload } = candidate;
  if (payload.base64) {
    const binary = atob(payload.base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    // Executables and unknown data are saved as .bin so they are not run by accident.
    const extension = (payload.detected_type && EXTENSIONS[payload.detected_type]) || (payload.kind === "TEXT" ? "txt" : "bin");
    saveBlob(new Blob([bytes], { type: "application/octet-stream" }), `stegolab-payload.${extension}`);
    return;
  }
  saveBlob(new Blob([payload.text ?? ""], { type: "text/plain;charset=utf-8" }), "stegolab-message.txt");
}

function payloadPreview(candidate: AutoCandidate, length = 80): string {
  const { payload } = candidate;
  if (payload.text !== null) {
    const flat = payload.text.replace(/\s+/g, " ").trim();
    return flat.length > length ? `${flat.slice(0, length)}…` : flat;
  }
  return payload.detected_type ? `${payload.detected_type}, ${formatBytes(payload.size_bytes)}` : `Binary data, ${formatBytes(payload.size_bytes)}`;
}

function EvidenceList({ candidate }: { candidate: AutoCandidate }) {
  return (
    <ul className="space-y-1.5">
      {candidate.evidence.map((item, index) => (
        <li key={`${item.check}-${index}`} className="flex items-start gap-2 text-xs leading-relaxed">
          {item.passed ? (
            <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-clean" aria-label="passed" />
          ) : (
            <XCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" aria-label="not passed" />
          )}
          <span className="text-muted">
            <span className="font-medium text-fg">{item.check}:</span> {item.detail}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Full view of one candidate: payload, method, parameters and evidence. */
export function CandidateDetail({ candidate, headline }: { candidate: AutoCandidate; headline?: string }) {
  const { payload } = candidate;
  const isText = payload.text !== null;

  return (
    <Card>
      <CardHeader
        icon={candidate.validation === "UNVERIFIED" ? <TriangleAlert className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
        title={headline ?? candidate.adapter_name}
        description={`${formatBytes(payload.size_bytes)} · ${candidate.adapter_name}`}
        actions={
          <>
            {isText && !payload.text_truncated && <CopyButton text={payload.text ?? ""} />}
            <Button variant="secondary" size="sm" onClick={() => downloadPayload(candidate)}>
              <Download className="h-3.5 w-3.5" aria-hidden />
              {isText && !payload.base64 ? "Save as .txt" : "Download"}
            </Button>
          </>
        }
      />
      <CardBody className="space-y-4">
        <div className="flex flex-wrap items-center gap-1.5">
          <ValidationBadge validation={candidate.validation} />
          <Badge>{FAMILY_LABEL[candidate.family]}</Badge>
          <Badge>{candidate.source === "PIXELS" ? "Hidden in pixels" : "Stored in file structure"}</Badge>
          {candidate.requires_key && (
            <Badge tone="warn">
              <KeyRound className="h-3 w-3" aria-hidden />
              Key or password needed
            </Badge>
          )}
        </div>

        {candidate.key_hint && <Callout tone="warning">{candidate.key_hint}</Callout>}

        {isText ? (
          <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-words rounded-lg border border-line bg-elevated/50 p-4 font-mono text-sm leading-relaxed text-fg">
            {payload.text}
          </pre>
        ) : (
          <div className="rounded-lg border border-line bg-elevated/50 p-4 text-sm text-muted">
            {payload.detected_type
              ? `Binary payload recognised as a ${payload.detected_type}.`
              : "Binary payload with no recognised file type."}{" "}
            Use Download to save it; StegoLab never opens or runs recovered files.
            {payload.archive_entries.length > 0 && (
              <ul className="mt-2 list-inside list-disc font-mono text-xs text-fg">
                {payload.archive_entries.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        {(payload.text_truncated || payload.truncated) && (
          <p className="text-xs text-muted">
            {payload.truncated
              ? "Only the first part of this payload was read (automatic extraction size limit)."
              : "The text is long; only the beginning is shown. Download saves the full payload."}
          </p>
        )}

        {candidate.notes.map((note) => (
          <Callout key={note} tone="warning">
            {note}
          </Callout>
        ))}

        <dl className="grid gap-x-6 gap-y-2 text-xs sm:grid-cols-2">
          <div>
            <dt className="text-faint">Method detected</dt>
            <dd className="mt-0.5 text-fg">{candidate.adapter_name}</dd>
          </div>
          <div>
            <dt className="text-faint">Parameters</dt>
            <dd className="mt-0.5 text-fg">{candidate.configuration}</dd>
          </div>
        </dl>

        <div>
          <p className="text-xs font-medium text-fg">Why this result was accepted</p>
          <p className="mt-0.5 text-xs leading-relaxed text-muted">{candidate.explanation}</p>
          <div className="mt-2">
            <EvidenceList candidate={candidate} />
          </div>
        </div>

        {candidate.also_found_by.length > 0 && (
          <p className="text-xs text-muted">
            The same bytes were also recovered by:{" "}
            {candidate.also_found_by.map((item) => `${item.adapter_name} (${item.configuration})`).join("; ")}.
          </p>
        )}
      </CardBody>
    </Card>
  );
}

/** Side-by-side table for several candidates; rows expand to the full detail. */
function CandidateComparison({ candidates, title, description }: { candidates: AutoCandidate[]; title: string; description: string }) {
  const [openId, setOpenId] = useState<string | null>(null);
  const open = candidates.find((candidate) => candidate.id === openId) ?? null;

  return (
    <div className="space-y-3">
      <Card>
        <CardHeader icon={<ListChecks className="h-4 w-4" />} title={title} description={description} />
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="border-b border-line text-faint">
              <tr>
                <th scope="col" className="px-5 py-2 font-medium">Status</th>
                <th scope="col" className="px-3 py-2 font-medium">Method and settings</th>
                <th scope="col" className="px-3 py-2 font-medium">Content</th>
                <th scope="col" className="px-5 py-2 font-medium"><span className="sr-only">Inspect</span></th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate) => (
                <tr key={candidate.id} className={cn("border-b border-line last:border-b-0", openId === candidate.id && "bg-elevated/50")}>
                  <td className="px-5 py-3 align-top">
                    <ValidationBadge validation={candidate.validation} />
                  </td>
                  <td className="px-3 py-3 align-top">
                    <p className="text-fg">{candidate.adapter_name}</p>
                    <p className="mt-0.5 text-muted">{candidate.configuration}</p>
                  </td>
                  <td className="max-w-xs px-3 py-3 align-top">
                    <p className="break-words font-mono text-fg">{payloadPreview(candidate)}</p>
                    <p className="mt-0.5 text-muted">
                      {candidate.evidence.filter((item) => item.passed).length} of {candidate.evidence.length} checks passed
                    </p>
                  </td>
                  <td className="px-5 py-3 text-right align-top">
                    <Button variant="ghost" size="sm" onClick={() => setOpenId(openId === candidate.id ? null : candidate.id)} aria-expanded={openId === candidate.id}>
                      {openId === candidate.id ? "Hide" : "Inspect"}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      {open && <CandidateDetail candidate={open} />}
    </div>
  );
}

function MethodRow({ method }: { method: AutoMethodTested }) {
  return (
    <li className="py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-fg">{method.name}</p>
        {method.applicable ? (
          <Badge tone={method.configurations_tested < method.configurations_total ? "warn" : "neutral"}>
            {method.configurations_tested} of {method.configurations_total} setting{method.configurations_total === 1 ? "" : "s"} tested
          </Badge>
        ) : (
          <Badge>Not applicable</Badge>
        )}
      </div>
      <p className="mt-0.5 text-xs leading-relaxed text-muted">{method.applicable ? method.detection : method.skipped_reason}</p>
      {method.compatibility && <p className="mt-0.5 text-xs leading-relaxed text-faint">Evidence: {method.compatibility}</p>}
      {method.required_parameters.length > 0 && (
        <p className="mt-0.5 text-xs text-warn">Requires: {method.required_parameters.join(", ")}</p>
      )}
    </li>
  );
}

function TestedReport({ result }: { result: AutoExtractResult }) {
  const outcomes = result.attempts.by_outcome;
  const rejected = result.attempts.details.filter((attempt) => attempt.outcome !== "SKIPPED");

  return (
    <Card className="overflow-hidden">
      <Collapsible
        title="What was tested"
        description={`${result.methods_tested.filter((m) => m.applicable).length} methods, ${result.attempts.total} checks in ${formatMs(result.processing_time_ms)}. ${
          outcomes.REJECTED ?? 0
        } rejected by framing or validation${outcomes.NOT_TESTED ? `, ${outcomes.NOT_TESTED} not tested (time limit)` : ""}.`}
      >
        <ul className="divide-y divide-line">
          {result.methods_tested.map((method) => (
            <MethodRow key={method.id} method={method} />
          ))}
        </ul>
        <Collapsible title="Every configuration and why it was rejected" className="mt-3 rounded-lg border border-line">
          <ul className="max-h-80 space-y-1 overflow-auto text-xs">
            {rejected.map((attempt, index) => (
              <li key={index} className="text-muted">
                <span className="font-medium text-fg">{attempt.adapter_name}</span>
                {attempt.configuration ? ` · ${attempt.configuration}` : ""} —{" "}
                <span className={attempt.outcome === "CANDIDATE" ? "text-clean" : undefined}>{attempt.outcome.toLowerCase().replace("_", " ")}</span>
                {attempt.reason ? `: ${attempt.reason}` : ""}
              </li>
            ))}
          </ul>
        </Collapsible>
        <p className="mt-3 text-xs leading-relaxed text-faint">{result.ranking_basis}</p>
      </Collapsible>
      <Collapsible title="Limitations">
        <ul className="list-inside list-disc space-y-1 text-xs leading-relaxed text-muted">
          {result.limitations.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </Collapsible>
    </Card>
  );
}

function SteganalysisNote({ result }: { result: AutoExtractResult }) {
  const signal = result.steganalysis;
  if (!signal.requested) return null;

  return (
    <Callout tone="info" title="Steganalysis (supporting signal only)">
      {signal.ran ? (
        <>
          The classifier rated this image <strong className="text-fg">{signal.predicted_class === "STEGO" ? "similar to images with hidden data" : "similar to clean images"}</strong>
          {signal.stego_probability !== null && <> (model output P(stego) = {formatPercent(signal.stego_probability)})</>}.{" "}
        </>
      ) : (
        <>Not run: {signal.skipped_reason} </>
      )}
      <span className="mt-1 block">{signal.note}</span>
    </Callout>
  );
}

function StatusBanner({ result }: { result: AutoExtractResult }) {
  switch (result.status) {
    case "VERIFIED":
      return <Callout tone="success" title="Hidden message found and verified">{result.summary}</Callout>;
    case "PLAUSIBLE":
      return <Callout tone="success" title="Hidden message found">{result.summary}</Callout>;
    case "AMBIGUOUS":
      return <Callout tone="warning" title="Several possible messages">{result.summary}</Callout>;
    case "UNVERIFIED":
      return <Callout tone="warning" title="Only uncertain data was recovered">{result.summary}</Callout>;
    default:
      return <Callout tone="info" title="No supported hidden message recovered">{result.summary}</Callout>;
  }
}

export function AutoExtractResultView({ result }: { result: AutoExtractResult }) {
  const best = result.best_candidate;
  const others = result.candidates.filter((candidate) => candidate.id !== best?.id);
  const customMetadata = result.metadata_findings.filter((item) => item.text.trim());

  return (
    <div className="space-y-4">
      <StatusBanner result={result} />

      {result.record.found && (
        <p className="text-xs text-muted">
          {result.record.source === "IMAGE_RECORD"
            ? "StegoLab has a record of how this image was made; those settings were tried first."
            : "This file is byte-identical to a stego image in your history; its recorded settings were tried first."}
        </p>
      )}

      {best && <CandidateDetail candidate={best} headline={best.validation === "VERIFIED" ? "Verified hidden message" : "Hidden message"} />}

      {result.status === "AMBIGUOUS" && (
        <CandidateComparison
          candidates={result.candidates}
          title="Compare the candidates"
          description="Each row was recovered with a different method or setting. Inspect them to decide which one is meaningful."
        />
      )}

      {result.status === "UNVERIFIED" && (
        <CandidateComparison
          candidates={result.candidates}
          title="Unverified candidates"
          description="These passed the format's framing checks but not content validation. They are most likely coincidences."
        />
      )}

      {best && others.length > 0 && (
        <Card className="overflow-hidden">
          <Collapsible
            title={`Other readings (${others.length})`}
            description="Additional data found with other methods or settings, usually weaker evidence."
          >
            <CandidateComparison candidates={others} title="Other readings" description={result.ranking_basis} />
          </Collapsible>
        </Card>
      )}

      {result.guidance.length > 0 && (
        <Card>
          <CardHeader
            icon={<FileSearch className="h-4 w-4" />}
            title={result.status === "NOT_FOUND" ? "What this means" : "If this isn't what you expected"}
            description="StegoLab only searched the methods listed under 'What was tested'. A negative result doesn't prove there is no message."
          />
          <CardBody>
            <ul className="list-inside list-disc space-y-1.5 text-sm leading-relaxed text-muted">
              {result.guidance.map((tip) => (
                <li key={tip}>{tip}</li>
              ))}
            </ul>
          </CardBody>
        </Card>
      )}

      {result.warnings.length > 0 && (
        <Callout tone="warning" title="Things to know about this file">
          <ul className="list-inside list-disc space-y-0.5">
            {result.warnings.map((warning) => (
              <li key={warning}>{warning}</li>
            ))}
          </ul>
        </Callout>
      )}

      {customMetadata.length > 0 && (
        <Card className="overflow-hidden">
          <Collapsible
            title={`Readable metadata in the file (${customMetadata.length})`}
            description="Text stored openly in the file's metadata. It is not hidden, but some tools put messages here."
            defaultOpen={result.status === "NOT_FOUND" && customMetadata.some((item) => !item.standard_key)}
          >
            <ul className="space-y-2">
              {customMetadata.map((item, index) => (
                <li key={`${item.key}-${index}`} className="rounded-lg border border-line p-3">
                  <p className="text-xs text-faint">
                    {item.location} · <span className="font-mono text-fg">{item.key}</span>
                    {item.standard_key && " · standard field"}
                  </p>
                  <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-xs text-fg">{item.text}</pre>
                  {item.truncated && <p className="mt-1 text-xs text-muted">Shortened for display.</p>}
                </li>
              ))}
            </ul>
          </Collapsible>
        </Card>
      )}

      <SteganalysisNote result={result} />

      <p className="text-xs text-muted">
        Image: {result.image.format}, {result.image.width} × {result.image.height} px, {result.image.mode}
        {result.image.bit_depth ? `, ${result.image.bit_depth}-bit` : ""}, {formatBytes(result.image.file_size_bytes)}
        {result.image.lossy ? " (lossy format)" : ""}.
      </p>

      <TestedReport result={result} />
    </div>
  );
}
