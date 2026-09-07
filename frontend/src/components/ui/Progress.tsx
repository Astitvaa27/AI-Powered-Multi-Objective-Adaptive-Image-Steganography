import { cn } from "@/lib/cn";

export function ProgressBar({
  value,
  tone = "accent",
  className,
  label,
}: {
  /** 0 to 1. */
  value: number;
  tone?: "accent" | "clean" | "stego" | "warn";
  className?: string;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(1, Number.isFinite(value) ? value : 0));

  const tones = {
    accent: "bg-accent",
    clean: "bg-clean",
    stego: "bg-stego",
    warn: "bg-warn",
  } as const;

  return (
    <div
      className={cn("h-2 w-full overflow-hidden rounded-full bg-elevated", className)}
      role="progressbar"
      aria-valuenow={Math.round(clamped * 100)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
    >
      <div
        className={cn("h-full rounded-full transition-all duration-500", tones[tone])}
        style={{ width: `${clamped * 100}%` }}
      />
    </div>
  );
}
