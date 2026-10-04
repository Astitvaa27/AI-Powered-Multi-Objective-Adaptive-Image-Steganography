import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

/** A single labelled number with an optional plain-language explanation. */
export function Stat({
  label,
  value,
  hint,
  info,
  tone = "neutral",
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  hint?: ReactNode;
  /** An InfoTip or similar, shown beside the label. */
  info?: ReactNode;
  tone?: "neutral" | "accent" | "clean" | "stego" | "warn";
  className?: string;
}) {
  const tones = {
    neutral: "text-fg",
    accent: "text-accent",
    clean: "text-clean",
    stego: "text-stego",
    warn: "text-warn",
  } as const;

  return (
    <div className={cn("rounded-lg border border-line bg-surface p-4", className)}>
      <p className="flex items-center gap-1.5 text-xs font-medium text-muted">
        {label}
        {info}
      </p>
      <p
        className={cn(
          "mt-1.5 font-mono text-xl font-semibold tabular-nums tracking-tight",
          tones[tone],
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs leading-relaxed text-muted">{hint}</p>}
    </div>
  );
}
