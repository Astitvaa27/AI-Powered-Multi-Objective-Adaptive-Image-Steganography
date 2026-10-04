import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export type Tone = "neutral" | "accent" | "clean" | "stego" | "warn";

const TONES: Record<Tone, string> = {
  neutral: "bg-elevated text-muted border-line",
  accent: "bg-accent-soft text-accent border-accent/25",
  clean: "bg-clean/10 text-clean border-clean/25",
  stego: "bg-stego/10 text-stego border-stego/25",
  warn: "bg-warn/10 text-warn border-warn/25",
};

export function Badge({
  children,
  tone = "neutral",
  className,
  title,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
  title?: string;
}) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** Maps a backend status string onto a tone and a readable label. */
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

export function statusLabel(status: string | null | undefined): string {
  const value = (status ?? "").toLowerCase();
  if (!value) return "Unknown";
  return value.charAt(0).toUpperCase() + value.slice(1);
}
