import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

type Tone = "neutral" | "accent" | "clean" | "stego" | "warn";

const TONES: Record<Tone, string> = {
  neutral: "bg-elevated text-muted border-line",
  accent: "bg-accent-soft text-accent border-accent/30",
  clean: "bg-clean/10 text-clean border-clean/30",
  stego: "bg-stego/10 text-stego border-stego/30",
  warn: "bg-warn/10 text-warn border-warn/30",
};

export function Badge({
  children,
  tone = "neutral",
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium uppercase tracking-wide",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Maps a backend status string onto a sensible tone. */
export function statusTone(status: string | null | undefined): Tone {
  switch ((status ?? "").toUpperCase()) {
    case "COMPLETED":
    case "GENERATED":
    case "ACTIVE":
      return "clean";
    case "FAILED":
      return "stego";
    case "PROCESSING":
    case "STARTED":
      return "warn";
    default:
      return "neutral";
  }
}
