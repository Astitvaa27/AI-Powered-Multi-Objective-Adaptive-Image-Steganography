import { ListChecks, Radar, Scale } from "lucide-react";
import type { AdaptiveComparison, AdaptiveSteganalysis } from "@/api/types";
import { DETECTOR_SCOPE_NOTE, STEGO_PROBABILITY_HELP, detectionVerdict } from "@/lib/describe";
import { formatNumber } from "@/lib/format";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { Callout } from "@/components/ui/Callout";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Collapsible } from "@/components/ui/Collapsible";
import { InfoTip } from "@/components/ui/InfoTip";
import { CandidateTable, ObjectiveBreakdown, evaluationSummary } from "./CandidateComparison";

/** "Why this method?" — the backend's own explanation plus every option. */
export function SelectionDetails({ comparison }: { comparison: AdaptiveComparison }) {
  return (
    <Card>
      <CardHeader
        icon={<Scale className="h-4 w-4" />}
        title="Why this method was chosen"
        description={evaluationSummary(comparison)}
      />
      <CardBody className="space-y-2.5 border-b border-line">
        <ul className="space-y-2">
          {comparison.explanation.map((line) => (
            <li key={line} className="flex gap-2.5 text-sm leading-relaxed text-fg">
              <ListChecks className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </CardBody>

      <CandidateTable comparison={comparison} />

      <div className="border-t border-line">
        <Collapsible
          title="Score breakdown"
          description="Each option's result on every goal, from 0 (worst) to 1 (best). Score = Σ weight × goal."
        >
          <ObjectiveBreakdown comparison={comparison} />
        </Collapsible>
        {comparison.limitations.length > 0 && (
          <Collapsible title="Limitations" description="What these measurements can and can't tell you">
            <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-muted">
              {comparison.limitations.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          </Collapsible>
        )}
      </div>
    </Card>
  );
}

/** The detector's view of the image that was kept. */
export function DetectionSummary({ steganalysis }: { steganalysis: AdaptiveSteganalysis }) {
  const verdict = detectionVerdict(steganalysis.stego_probability);
  const delta =
    steganalysis.stego_probability !== null && steganalysis.cover_stego_probability !== null
      ? steganalysis.stego_probability - steganalysis.cover_stego_probability
      : null;

  return (
    <Card>
      <CardHeader
        icon={<Radar className="h-4 w-4" />}
        title="How detectable is it?"
        description="The steganalysis detector was run on the final image."
        actions={
          steganalysis.analysis_session_id && (
            <ButtonLink
              to={`/history/analyses/${steganalysis.analysis_session_id}`}
              variant="secondary"
              size="sm"
            >
              Full report
            </ButtonLink>
          )
        }
      />
      <CardBody className="space-y-4">
        {!steganalysis.available ? (
          <Callout tone="warning" title="Detection wasn't available">
            {steganalysis.error ?? "The detector could not be run."} The method was
            chosen using the remaining goals only.
          </Callout>
        ) : (
          <>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <p className="text-xs font-medium text-muted">Detector verdict</p>
                <Badge tone={verdict.tone} className="mt-1.5">
                  {verdict.label}
                </Badge>
              </div>
              <div>
                <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
                  P(stego) of this image
                  <InfoTip label="About P(stego)">{STEGO_PROBABILITY_HELP}</InfoTip>
                </p>
                <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-fg">
                  {formatNumber(steganalysis.stego_probability, 3)}
                </p>
              </div>
              <div>
                <p className="text-xs font-medium text-muted">P(stego) of the original</p>
                <p className="mt-1 font-mono text-xl font-semibold tabular-nums text-muted">
                  {formatNumber(steganalysis.cover_stego_probability, 3)}
                  {delta !== null && (
                    <span className="ml-2 text-sm">
                      ({delta > 0 ? "+" : ""}
                      {formatNumber(delta, 3)})
                    </span>
                  )}
                </p>
              </div>
            </div>
            <p className="text-xs leading-relaxed text-muted">
              Compare the two numbers: the detector&apos;s score depends on the picture
              itself, so a change relative to the original matters more than the
              absolute value. {DETECTOR_SCOPE_NOTE}
            </p>
            {steganalysis.requested && steganalysis.error && (
              <Callout tone="warning">Saving the full report failed: {steganalysis.error}</Callout>
            )}
          </>
        )}
      </CardBody>
    </Card>
  );
}
