import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function MetricCard({
  label,
  value,
  hint,
  icon,
  tone = "neutral",
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: ReactNode;
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
    <div className={cn("panel p-4", className)}>
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase tracking-wide text-muted">
          {label}
        </p>
        {icon && <span className="text-faint">{icon}</span>}
      </div>
      <p
        className={cn(
          "mt-2 font-mono text-2xl font-semibold tabular-nums tracking-tight",
          tones[tone],
        )}
      >
        {value}
      </p>
      {hint && <p className="mt-1 text-xs text-faint">{hint}</p>}
    </div>
  );
}
