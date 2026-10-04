import { cn } from "@/lib/cn";

/**
 * The StegoLab mark: a 3×3 pixel grid with one brighter pixel — a message
 * hidden in plain sight.
 */
export function LogoMark({ className }: { className?: string }) {
  const cells = [0, 1, 2].flatMap((row) => [0, 1, 2].map((col) => ({ row, col })));

  return (
    <svg
      viewBox="0 0 32 32"
      className={cn("h-8 w-8 shrink-0", className)}
      aria-hidden
      focusable="false"
    >
      <rect width="32" height="32" rx="8" className="fill-accent" />
      {cells.map(({ row, col }) => (
        <rect
          key={`${row}-${col}`}
          x={7 + col * 6.5}
          y={7 + row * 6.5}
          width="5"
          height="5"
          rx="1.2"
          className="fill-on-accent"
          opacity={row === 1 && col === 2 ? 1 : 0.4}
        />
      ))}
    </svg>
  );
}

export function Logo({ className, size = "md" }: { className?: string; size?: "md" | "lg" }) {
  return (
    <span className={cn("inline-flex items-center gap-2.5", className)}>
      <LogoMark className={size === "lg" ? "h-10 w-10" : "h-8 w-8"} />
      <span
        className={cn(
          "font-semibold tracking-tight text-fg",
          size === "lg" ? "text-xl" : "text-base",
        )}
      >
        StegoLab
      </span>
    </span>
  );
}
