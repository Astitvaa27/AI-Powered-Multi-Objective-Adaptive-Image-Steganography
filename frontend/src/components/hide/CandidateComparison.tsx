import type { AdaptiveCandidate, AdaptiveComparison } from "@/api/types";
import { methodWithParams } from "@/lib/describe";
import { cn } from "@/lib/cn";
import { formatMs, formatNumber, formatPercent } from "@/lib/format";
import { Badge, type Tone } from "@/components/ui/Badge";
import { InfoTip } from "@/components/ui/InfoTip";
import { ProgressBar } from "@/components/ui/Progress";
import { OBJECTIVE_INFO } from "./presets";

const STATUS: Record<AdaptiveCandidate["status"], { label: string; tone: Tone }> = {
  EVALUATED: { label: "Passed", tone: "clean" },
  SKIPPED: { label: "Didn't fit", tone: "warn" },
  REJECTED: { label: "Failed check", tone: "stego" },
  FAILED: { label: "Error", tone: "stego" },
  PENDING: { label: "Not run", tone: "neutral" },
};

export function candidateName(candidate: AdaptiveCandidate): string {
  return methodWithParams(
    candidate.method,
    candidate.parameters.channel_mode,
    candidate.parameters.lsb_bits,
  );
}

function ordered(candidates: AdaptiveCandidate[]) {
  return [...candidates].sort((a, b) => (a.rank ?? Infinity) - (b.rank ?? Infinity));
}

function psnrText(candidate: AdaptiveCandidate) {
  if (candidate.psnr !== null) return `${formatNumber(candidate.psnr, 1)} dB`;
  return candidate.feasible ? "∞" : "—";
}

function CandidateTags({ candidate }: { candidate: AdaptiveCandidate }) {
  return (
    <span className="flex flex-wrap items-center gap-1.5">
      {candidate.selected && <Badge tone="accent">Chosen</Badge>}
      {candidate.pareto_optimal && (
        <Badge title="No other option is at least as good on every goal and better on one.">
          Pareto-optimal
        </Badge>
      )}
    </span>
  );
}

/** Every option the optimiser tried, with its real measurements. */
export function CandidateTable({ comparison }: { comparison: AdaptiveComparison }) {
  const rows = ordered(comparison.candidates);

  return (
    <>
      {/* Desktop table */}
      <div className="hidden overflow-x-auto md:block">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-xs text-muted">
            <tr>
              <th scope="col" className="px-5 py-2.5 font-medium">#</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Option</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Result</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Quality</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Values changed</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Room used</th>
              <th scope="col" className="px-3 py-2.5 font-medium">P(stego)</th>
              <th scope="col" className="px-3 py-2.5 font-medium">Survives JPEG</th>
              <th scope="col" className="px-5 py-2.5 text-right font-medium">Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((candidate) => (
              <tr
                key={candidate.key}
                className={cn("align-top", candidate.selected && "bg-accent-soft/50")}
              >
                <td className="px-5 py-3 font-mono text-xs text-muted">{candidate.rank ?? "—"}</td>
                <td className="min-w-[14rem] px-3 py-3">
                  <p className="font-medium text-fg">{candidateName(candidate)}</p>
                  <div className="mt-1">
                    <CandidateTags candidate={candidate} />
                  </div>
                  {candidate.failure_reason && (
                    <p className="mt-1 max-w-xs text-xs leading-relaxed text-muted">
                      {candidate.failure_reason}
                    </p>
                  )}
                </td>
                <td className="px-3 py-3">
                  <Badge tone={STATUS[candidate.status].tone}>{STATUS[candidate.status].label}</Badge>
                </td>
                <td className="px-3 py-3 font-mono text-xs tabular-nums text-fg">{psnrText(candidate)}</td>
                <td className="px-3 py-3 font-mono text-xs tabular-nums text-fg">
                  {formatPercent(candidate.change_rate, 2)}
                </td>
                <td className="px-3 py-3 font-mono text-xs tabular-nums text-fg">
                  {formatPercent(candidate.capacity_used_ratio, 2)}
                </td>
                <td className="px-3 py-3 font-mono text-xs tabular-nums text-fg">
                  {formatNumber(candidate.stego_probability, 3)}
                </td>
                <td className="px-3 py-3 font-mono text-xs tabular-nums text-fg">
                  {formatPercent(candidate.robustness_bit_accuracy, 0)}
                </td>
                <td className="px-5 py-3 text-right font-mono text-sm font-semibold tabular-nums text-fg">
                  {formatNumber(candidate.score, 3)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile cards */}
      <ul className="divide-y divide-line md:hidden">
        {rows.map((candidate) => (
          <li key={candidate.key} className={cn("px-4 py-4", candidate.selected && "bg-accent-soft/50")}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-medium text-fg">{candidateName(candidate)}</p>
                <div className="mt-1">
                  <CandidateTags candidate={candidate} />
                </div>
              </div>
              <Badge tone={STATUS[candidate.status].tone}>{STATUS[candidate.status].label}</Badge>
            </div>
            {candidate.failure_reason ? (
              <p className="mt-2 text-xs leading-relaxed text-muted">{candidate.failure_reason}</p>
            ) : (
              <dl className="mt-3 grid grid-cols-3 gap-x-3 gap-y-2 text-xs">
                <MobileMetric label="Quality" value={psnrText(candidate)} />
                <MobileMetric label="Changed" value={formatPercent(candidate.change_rate, 2)} />
                <MobileMetric label="P(stego)" value={formatNumber(candidate.stego_probability, 3)} />
                <MobileMetric label="Room used" value={formatPercent(candidate.capacity_used_ratio, 2)} />
                <MobileMetric label="JPEG" value={formatPercent(candidate.robustness_bit_accuracy, 0)} />
                <MobileMetric label="Score" value={formatNumber(candidate.score, 3)} strong />
              </dl>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}

function MobileMetric({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd className={cn("font-mono tabular-nums text-fg", strong && "font-semibold")}>{value}</dd>
    </div>
  );
}

/** How each passing option scored on each goal (0 = worst, 1 = best). */
export function ObjectiveBreakdown({ comparison }: { comparison: AdaptiveComparison }) {
  const rows = ordered(comparison.candidates).filter((candidate) => candidate.feasible);
  const objectives = comparison.objectives_evaluated;

  if (rows.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-muted">
        {objectives.map((name) => (
          <span key={name} className="inline-flex items-center gap-1.5">
            <span className="font-medium text-fg">{OBJECTIVE_INFO[name].label}</span>
            weight {formatPercent(comparison.weights[name], 0)}
            <InfoTip label={`About ${OBJECTIVE_INFO[name].label}`}>{OBJECTIVE_INFO[name].help}</InfoTip>
          </span>
        ))}
      </div>

      <div className="space-y-4">
        {rows.map((candidate) => (
          <div key={candidate.key}>
            <p className="mb-2 flex flex-wrap items-center gap-2 text-sm font-medium text-fg">
              {candidateName(candidate)}
              {candidate.selected && <Badge tone="accent">Chosen</Badge>}
              <span className="ml-auto font-mono text-xs text-muted">
                score {formatNumber(candidate.score, 3)}
              </span>
            </p>
            <div className="grid gap-x-6 gap-y-2 sm:grid-cols-2 lg:grid-cols-3">
              {objectives.map((name) => {
                const value = candidate.objectives[name] ?? 0;
                return (
                  <div key={name} className="flex items-center gap-2">
                    <span className="w-28 shrink-0 text-xs text-muted">{OBJECTIVE_INFO[name].label}</span>
                    <ProgressBar
                      value={value}
                      tone={candidate.selected ? "accent" : "clean"}
                      className="flex-1"
                      label={`${OBJECTIVE_INFO[name].label} for ${candidateName(candidate)}`}
                    />
                    <span className="w-9 text-right font-mono text-xs tabular-nums text-fg">
                      {formatNumber(value, 2)}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function evaluationSummary(comparison: AdaptiveComparison) {
  const passed = comparison.candidates.filter((candidate) => candidate.feasible).length;
  const totalMs = comparison.candidates.reduce(
    (sum, candidate) => sum + (candidate.processing_time_ms ?? 0),
    0,
  );
  return `${comparison.candidates.length} options tried · ${passed} passed every check · ${formatMs(totalMs)} of processing`;
}
