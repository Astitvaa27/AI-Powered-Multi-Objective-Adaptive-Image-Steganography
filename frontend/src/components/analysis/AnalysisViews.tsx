import { useState } from "react";
import { Info, ShieldAlert, ShieldCheck } from "lucide-react";
import type { FeatureMap, SuspiciousRegion } from "@/api/types";
import { groupFeatures } from "@/lib/featureCatalog";
import { DETECTOR_SCOPE_NOTE, STEGO_PROBABILITY_HELP } from "@/lib/describe";
import { cn } from "@/lib/cn";
import { formatNumber, formatPercent } from "@/lib/format";
import { Badge } from "@/components/ui/Badge";
import { Collapsible } from "@/components/ui/Collapsible";
import { InfoTip } from "@/components/ui/InfoTip";
import { ProgressBar } from "@/components/ui/Progress";
import { EmptyState } from "@/components/ui/States";
import { regionKey, regionTone } from "@/components/images/ImagePreview";

/** The headline result of an analysis, in plain language. */
export function AnalysisVerdict({
  predictedClass,
  probabilities,
}: {
  predictedClass: string;
  probabilities: Record<string, number> | null;
}) {
  const flagged = predictedClass.toUpperCase() === "STEGO";
  const stego = probabilities?.STEGO ?? null;
  const clean = probabilities?.CLEAN ?? null;

  return (
    <section
      className={cn(
        "rounded-xl border p-5 sm:p-6",
        flagged ? "border-stego/30 bg-stego/5" : "border-clean/30 bg-clean/5",
      )}
      aria-live="polite"
    >
      <div className="flex flex-wrap items-start gap-4">
        <span
          className={cn(
            "flex h-11 w-11 shrink-0 items-center justify-center rounded-full",
            flagged ? "bg-stego/15 text-stego" : "bg-clean/15 text-clean",
          )}
        >
          {flagged ? <ShieldAlert className="h-6 w-6" /> : <ShieldCheck className="h-6 w-6" />}
        </span>
        <div className="min-w-0 flex-1">
          <h2 className={cn("text-lg font-semibold", flagged ? "text-stego" : "text-clean")}>
            {flagged ? "Likely contains hidden data" : "No hidden data detected"}
          </h2>
          <p className="mt-1 text-sm leading-relaxed text-muted">
            {flagged
              ? "The detector's statistics for this image look more like images with hidden data than without. This is an estimate, not proof."
              : "The detector's statistics for this image look like ordinary images. That doesn't guarantee nothing is hidden — some methods are hard for this detector to see."}
          </p>
        </div>
        {stego !== null && (
          <div className="text-left sm:text-right">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted sm:justify-end">
              Probability of hidden data
              <InfoTip label="About this probability">{STEGO_PROBABILITY_HELP}</InfoTip>
            </p>
            <p className={cn("font-mono text-3xl font-semibold tabular-nums", flagged ? "text-stego" : "text-clean")}>
              {formatPercent(stego, 1)}
            </p>
          </div>
        )}
      </div>

      {stego !== null && clean !== null && (
        <div className="mt-5 space-y-2">
          <div className="flex h-2.5 overflow-hidden rounded-full bg-elevated" aria-hidden>
            <div className="bg-clean" style={{ width: `${clean * 100}%` }} />
            <div className="bg-stego" style={{ width: `${stego * 100}%` }} />
          </div>
          <div className="flex justify-between text-xs text-muted">
            <span>Ordinary image {formatPercent(clean, 1)}</span>
            <span>Hidden data {formatPercent(stego, 1)}</span>
          </div>
        </div>
      )}

      <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-muted">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
        {DETECTOR_SCOPE_NOTE}
      </p>
    </section>
  );
}

/** Ranked areas with unusual pixel-bit statistics. */
export function RegionList({
  regions,
  highlightedRegionId,
  onRegionHover,
}: {
  regions: SuspiciousRegion[];
  highlightedRegionId?: string | null;
  onRegionHover?: (id: string | null) => void;
}) {
  const [showAll, setShowAll] = useState(false);

  if (regions.length === 0) {
    return (
      <EmptyState
        title="No unusual areas found"
        description="The area scan didn't flag any blocks with unusual pixel-bit statistics."
      />
    );
  }

  const visible = showAll ? regions : regions.slice(0, 10);

  return (
    <div>
      <p className="border-b border-line px-5 py-3 text-xs leading-relaxed text-muted">
        <span className="font-medium text-fg">These are areas worth a closer look, not proof.</span>{" "}
        Each block is scored by how unusual its pixel bits are (0–1). A high score
        doesn&apos;t mean a message is stored there. Hover a row to highlight it on
        the image.
      </p>
      <ul className="divide-y divide-line">
        {visible.map((region, index) => {
          const key = regionKey(region, index);
          const score = region.suspicion_score ?? 0;
          return (
            <li
              key={key}
              onMouseEnter={() => onRegionHover?.(key)}
              onMouseLeave={() => onRegionHover?.(null)}
              className={cn(
                "flex flex-wrap items-center gap-x-4 gap-y-2 px-5 py-2.5 text-sm transition-colors",
                highlightedRegionId === key ? "bg-accent-soft/60" : "hover:bg-elevated/50",
              )}
            >
              <span
                className="flex h-6 w-6 shrink-0 items-center justify-center rounded text-xs font-semibold text-white"
                style={{ backgroundColor: regionTone(region.suspicion_score) }}
              >
                {index + 1}
              </span>
              <span className="min-w-[9rem] flex-1 font-mono text-xs text-muted">
                at ({region.x}, {region.y}) · {region.width}×{region.height} px
              </span>
              <span className="flex w-40 items-center gap-2">
                <ProgressBar
                  value={score}
                  tone={score >= 0.66 ? "stego" : score >= 0.33 ? "warn" : "accent"}
                  label={`Anomaly score for area ${index + 1}`}
                />
                <span className="w-11 text-right font-mono text-xs tabular-nums text-fg">
                  {score.toFixed(3)}
                </span>
              </span>
            </li>
          );
        })}
      </ul>
      {regions.length > 10 && (
        <div className="border-t border-line px-5 py-2.5 text-center">
          <button
            type="button"
            onClick={() => setShowAll((value) => !value)}
            className="text-sm font-medium text-accent hover:underline"
          >
            {showAll ? "Show top 10 only" : `Show all ${regions.length} areas`}
          </button>
        </div>
      )}
    </div>
  );
}

/** The measurements the detector used, grouped and explained. */
export function FeatureAnalysis({ features }: { features: FeatureMap | null }) {
  if (!features || Object.keys(features).length === 0) {
    return (
      <EmptyState
        title="No detector inputs stored"
        description="Measurements are saved with each completed analysis."
      />
    );
  }

  const groups = groupFeatures(features);

  return (
    <div>
      <p className="border-b border-line px-5 py-3 text-xs leading-relaxed text-muted">
        The detector made its decision from these {Object.keys(features).length} measurements.
        Technical names are shown beneath each label.
      </p>
      {groups.map((group, index) => (
        <Collapsible
          key={group.id}
          title={group.title}
          description={group.blurb}
          defaultOpen={index === 0}
          badge={<Badge>{group.entries.length}</Badge>}
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {group.entries.map(({ descriptor, value }) => (
              <div key={descriptor.key} className="rounded-lg border border-line bg-elevated/40 p-3">
                <p className="text-sm font-medium text-fg">{descriptor.label}</p>
                <p className="mt-1 font-mono text-lg font-semibold tabular-nums text-fg">
                  {formatNumber(value, descriptor.digits ?? 4)}
                </p>
                <p className="mt-0.5 font-mono text-[11px] text-faint">{descriptor.key}</p>
                <p className="mt-1.5 text-xs leading-relaxed text-muted">{descriptor.description}</p>
              </div>
            ))}
          </div>
        </Collapsible>
      ))}
    </div>
  );
}
