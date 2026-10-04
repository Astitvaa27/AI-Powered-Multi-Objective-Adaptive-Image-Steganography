import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Circle, MinusCircle } from "lucide-react";
import type { AutoExtractEvent, AutoStageId } from "@/api/types";
import { cn } from "@/lib/cn";
import { formatMs } from "@/lib/format";
import { ProgressBar } from "@/components/ui/Progress";
import { Spinner } from "@/components/ui/States";

export const STAGE_ORDER: { id: AutoStageId; label: string }[] = [
  { id: "validate", label: "Validating image" },
  { id: "records", label: "Checking StegoLab records" },
  { id: "containers", label: "Checking known formats" },
  { id: "search", label: "Searching supported extraction methods" },
  { id: "validate_candidates", label: "Validating candidate payloads" },
  { id: "steganalysis", label: "Steganalysis (supporting signal)" },
  { id: "result", label: "Preparing the result" },
];

export interface StageState {
  status: "pending" | "running" | "completed" | "partial" | "skipped";
  detail: string | null;
  durationMs?: number;
  progress?: { done: number; total: number };
}

export type StageMap = Record<AutoStageId, StageState>;

export function initialStages(): StageMap {
  return Object.fromEntries(
    STAGE_ORDER.map(({ id }) => [id, { status: "pending", detail: null }]),
  ) as StageMap;
}

/** Fold one backend event into the stage map. */
export function applyStageEvent(stages: StageMap, event: AutoExtractEvent): StageMap {
  if (event.type !== "stage") return stages;
  const previous = stages[event.stage];
  return {
    ...stages,
    [event.stage]: {
      status: event.status,
      detail: event.detail ?? previous.detail,
      durationMs: event.duration_ms ?? previous.durationMs,
      progress: event.progress ?? previous.progress,
    },
  };
}

function StageIcon({ status }: { status: StageState["status"] }) {
  switch (status) {
    case "running":
      return <Spinner className="h-4 w-4" />;
    case "completed":
      return <CheckCircle2 className="h-4 w-4 text-clean" aria-hidden />;
    case "partial":
      return <AlertTriangle className="h-4 w-4 text-warn" aria-hidden />;
    case "skipped":
      return <MinusCircle className="h-4 w-4 text-faint" aria-hidden />;
    default:
      return <Circle className="h-4 w-4 text-line-strong" aria-hidden />;
  }
}

const STATUS_TEXT: Record<StageState["status"], string> = {
  pending: "waiting",
  running: "in progress",
  completed: "done",
  partial: "stopped early",
  skipped: "skipped",
};

/**
 * Live view of the detection stages. Every state shown here comes from a
 * backend event; nothing is advanced on a timer.
 */
export function DetectionProgress({ stages }: { stages: StageMap }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="px-5 py-5" role="status" aria-live="polite" aria-busy="true">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-fg">Detecting hidden data…</p>
        <span className="font-mono text-xs tabular-nums text-muted">{elapsed}s</span>
      </div>
      <ol className="mt-4 space-y-3">
        {STAGE_ORDER.map(({ id, label }) => {
          const stage = stages[id];
          const progress = stage.progress;
          return (
            <li key={id} className="flex items-start gap-3">
              <span className="mt-0.5 shrink-0">
                <StageIcon status={stage.status} />
              </span>
              <div className="min-w-0 flex-1">
                <p
                  className={cn(
                    "text-sm",
                    stage.status === "pending" ? "text-faint" : "text-fg",
                    stage.status === "running" && "font-medium",
                  )}
                >
                  {label}
                  <span className="sr-only"> — {STATUS_TEXT[stage.status]}</span>
                  {stage.durationMs !== undefined && stage.status !== "running" && (
                    <span className="ml-2 font-mono text-xs text-faint">{formatMs(stage.durationMs)}</span>
                  )}
                </p>
                {stage.detail && stage.status !== "pending" && (
                  <p className="mt-0.5 text-xs leading-relaxed text-muted">{stage.detail}</p>
                )}
                {progress && progress.total > 0 && stage.status === "running" && (
                  <div className="mt-1.5 flex items-center gap-2">
                    <ProgressBar
                      value={progress.done / progress.total}
                      className="h-1.5 max-w-xs"
                      label={`${progress.done} of ${progress.total} configurations tested`}
                    />
                    <span className="font-mono text-xs tabular-nums text-muted">
                      {progress.done}/{progress.total}
                    </span>
                  </div>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
