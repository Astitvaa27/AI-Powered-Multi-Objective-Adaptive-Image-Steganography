import { useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Info, ShieldAlert, ShieldCheck } from "lucide-react";
import type { FeatureMap, SuspiciousRegion } from "@/api/types";
import { groupFeatures } from "@/lib/featureCatalog";
import { cn } from "@/lib/cn";
import { formatNumber, formatPercent } from "@/lib/format";
import { Badge } from "./ui/Badge";
import { Collapsible } from "./ui/Collapsible";
import { ProgressBar } from "./ui/Progress";
import { EmptyState } from "./ui/States";

/* -------------------------------------------------------------------- */
/* Detection verdict                                                     */
/* -------------------------------------------------------------------- */

export function DetectionResult({
  predictedClass,
  confidence,
  probabilities,
  className,
}: {
  predictedClass: string;
  confidence: number | null;
  probabilities: Record<string, number> | null;
  className?: string;
}) {
  const isStego = predictedClass.toUpperCase() === "STEGO";

  const cleanProbability = probabilities?.CLEAN ?? null;
  const stegoProbability = probabilities?.STEGO ?? null;

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border",
        isStego ? "border-stego/40 bg-stego/5" : "border-clean/40 bg-clean/5",
        className,
      )}
    >
      <div className="flex flex-wrap items-center gap-5 p-6">
        <span
          className={cn(
            "flex h-14 w-14 shrink-0 items-center justify-center rounded-full",
            isStego ? "bg-stego/15 text-stego" : "bg-clean/15 text-clean",
          )}
        >
          {isStego ? (
            <ShieldAlert className="h-7 w-7" />
          ) : (
            <ShieldCheck className="h-7 w-7" />
          )}
        </span>

        <div className="min-w-0 flex-1">
          <p className="text-[11px] font-medium uppercase tracking-widest text-muted">
            Classification result
          </p>
          <p
            className={cn(
              "mt-0.5 text-2xl font-semibold tracking-tight",
              isStego ? "text-stego" : "text-clean",
            )}
          >
            {isStego ? "Stego detected" : "Clean"}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-muted">
            {isStego
              ? "The classifier assigned this image to the STEGO class. This is a statistical classification, not proof of a hidden payload."
              : "The classifier assigned this image to the CLEAN class. Detector performance is payload-dependent, so a clean result does not guarantee the absence of embedding."}
          </p>
        </div>

        <div className="shrink-0 text-right">
          <p className="text-[11px] font-medium uppercase tracking-widest text-muted">
            Confidence
          </p>
          <p
            className={cn(
              "font-mono text-4xl font-semibold tabular-nums",
              isStego ? "text-stego" : "text-clean",
            )}
          >
            {formatPercent(confidence, 1)}
          </p>
        </div>
      </div>

      {(cleanProbability !== null || stegoProbability !== null) && (
        <div className="grid gap-4 border-t border-line/60 bg-surface/40 p-5 sm:grid-cols-2">
          <ProbabilityRow
            label="CLEAN probability"
            value={cleanProbability}
            tone="clean"
          />
          <ProbabilityRow
            label="STEGO probability"
            value={stegoProbability}
            tone="stego"
          />
        </div>
      )}
    </div>
  );
}

function ProbabilityRow({
  label,
  value,
  tone,
}: {
  label: string;
  value: number | null;
  tone: "clean" | "stego";
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-2">
        <span className="text-xs font-medium text-muted">{label}</span>
        <span
          className={cn(
            "font-mono text-sm font-semibold tabular-nums",
            tone === "clean" ? "text-clean" : "text-stego",
          )}
        >
          {formatPercent(value, 1)}
        </span>
      </div>
      <ProgressBar value={value ?? 0} tone={tone} label={label} />
    </div>
  );
}

/* -------------------------------------------------------------------- */
/* Class probability chart                                               */
/* -------------------------------------------------------------------- */

export function ProbabilityChart({
  probabilities,
}: {
  probabilities: Record<string, number>;
}) {
  const data = Object.entries(probabilities).map(([name, value]) => ({
    name,
    value,
  }));

  if (data.length === 0) {
    return (
      <EmptyState title="No probabilities returned" className="py-8" />
    );
  }

  return (
    <div className="h-52 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 8, right: 40, bottom: 8, left: 8 }}
        >
          <XAxis
            type="number"
            domain={[0, 1]}
            tickFormatter={(value: number) => `${Math.round(value * 100)}%`}
            tick={{ fontSize: 11, fill: "rgb(var(--muted))" }}
            axisLine={{ stroke: "rgb(var(--line))" }}
            tickLine={false}
          />
          <YAxis
            type="category"
            dataKey="name"
            width={64}
            tick={{ fontSize: 12, fill: "rgb(var(--fg))" }}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            cursor={{ fill: "rgb(var(--elevated))" }}
            formatter={(value: number) => [formatPercent(value, 2), "Probability"]}
            contentStyle={{
              background: "rgb(var(--surface))",
              border: "1px solid rgb(var(--line))",
              borderRadius: 8,
              fontSize: 12,
              color: "rgb(var(--fg))",
            }}
          />
          <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={28}>
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={
                  entry.name.toUpperCase() === "STEGO"
                    ? "rgb(var(--stego))"
                    : "rgb(var(--clean))"
                }
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* -------------------------------------------------------------------- */
/* Feature analysis                                                      */
/* -------------------------------------------------------------------- */

export function FeatureAnalysis({ features }: { features: FeatureMap | null }) {
  if (!features || Object.keys(features).length === 0) {
    return (
      <EmptyState
        title="No feature vector available"
        description="Feature values are stored with each completed analysis session."
      />
    );
  }

  const groups = groupFeatures(features);

  return (
    <div>
      <div className="flex items-center gap-2 border-b border-line px-5 py-3 text-xs text-muted">
        <Info className="h-3.5 w-3.5 shrink-0 text-faint" />
        <span>
          {Object.keys(features).length} features were supplied to the
          classifier. Backend feature names are preserved beneath each label.
        </span>
      </div>

      {groups.map((group, index) => (
        <Collapsible
          key={group.id}
          title={group.title}
          description={group.blurb}
          defaultOpen={index === 0}
          badge={
            <Badge tone="neutral">{group.entries.length}</Badge>
          }
        >
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {group.entries.map(({ descriptor, value }) => (
              <div
                key={descriptor.key}
                className="rounded-lg border border-line bg-elevated/40 p-3"
              >
                <p className="text-xs font-medium text-fg">{descriptor.label}</p>
                <p className="mt-1 font-mono text-lg font-semibold tabular-nums text-accent">
                  {formatNumber(value, descriptor.digits ?? 4)}
                </p>
                <p className="mt-1 font-mono text-[10px] text-faint">
                  {descriptor.key}
                </p>
                <p className="mt-1.5 text-[11px] leading-relaxed text-muted">
                  {descriptor.description}
                </p>
              </div>
            ))}
          </div>
        </Collapsible>
      ))}
    </div>
  );
}

/* -------------------------------------------------------------------- */
/* Candidate regions                                                     */
/* -------------------------------------------------------------------- */

export function SuspiciousRegionPanel({
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
        title="No candidate regions ranked"
        description="The region detector did not surface any local LSB anomalies for this image."
      />
    );
  }

  const visible = showAll ? regions : regions.slice(0, 10);

  return (
    <div>
      <div className="flex items-start gap-2 border-b border-line bg-warn/5 px-5 py-3">
        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-warn" />
        <p className="text-[11px] leading-relaxed text-muted">
          <span className="font-medium text-fg">
            These are candidate regions, not confirmed embedding locations.
          </span>{" "}
          Each box is ranked by local LSB anomaly score. A high score indicates
          statistically unusual bit behaviour in that block — it does not
          identify where a payload is stored.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4 border-b border-line px-5 py-2.5 text-[11px] text-muted">
        <span className="font-medium uppercase tracking-wide">Legend</span>
        <LegendSwatch color="rgb(var(--stego))" label="High anomaly (≥ 0.66)" />
        <LegendSwatch color="rgb(var(--warn))" label="Medium (0.33 – 0.66)" />
        <LegendSwatch color="rgb(var(--accent))" label="Low (< 0.33)" />
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="border-b border-line text-[11px] uppercase tracking-wide text-faint">
            <tr>
              <th scope="col" className="px-5 py-2 font-medium">Rank</th>
              <th scope="col" className="px-3 py-2 font-medium">Position (x, y)</th>
              <th scope="col" className="px-3 py-2 font-medium">Size</th>
              <th scope="col" className="px-3 py-2 font-medium">Type</th>
              <th scope="col" className="px-5 py-2 font-medium">Anomaly score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {visible.map((region, index) => {
              const key = region.id ?? `${region.x}-${region.y}-${index}`;
              const score = region.suspicion_score ?? 0;

              return (
                <tr
                  key={key}
                  onMouseEnter={() => onRegionHover?.(key)}
                  onMouseLeave={() => onRegionHover?.(null)}
                  className={cn(
                    "transition-colors",
                    highlightedRegionId === key
                      ? "bg-accent-soft/60"
                      : "hover:bg-elevated/50",
                  )}
                >
                  <td className="px-5 py-2 font-mono text-faint">#{index + 1}</td>
                  <td className="px-3 py-2 font-mono text-fg">
                    {region.x}, {region.y}
                  </td>
                  <td className="px-3 py-2 font-mono text-muted">
                    {region.width} × {region.height}
                  </td>
                  <td className="px-3 py-2">
                    <Badge tone="neutral">
                      {region.region_type ?? "candidate"}
                    </Badge>
                  </td>
                  <td className="px-5 py-2">
                    <div className="flex items-center gap-2">
                      <ProgressBar
                        value={score}
                        tone={score >= 0.66 ? "stego" : score >= 0.33 ? "warn" : "accent"}
                        className="w-24"
                        label={`Anomaly score for candidate region ${index + 1}`}
                      />
                      <span className="font-mono tabular-nums text-fg">
                        {score.toFixed(3)}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {regions.length > 10 && (
        <div className="border-t border-line px-5 py-2.5 text-center">
          <button
            type="button"
            onClick={() => setShowAll((value) => !value)}
            className="text-[11px] font-medium text-accent transition-opacity hover:opacity-80"
          >
            {showAll
              ? "Show top 10 only"
              : `Show all ${regions.length} candidate regions`}
          </button>
        </div>
      )}
    </div>
  );
}

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span
        className="h-2.5 w-2.5 rounded-sm border-2"
        style={{ borderColor: color }}
      />
      {label}
    </span>
  );
}
