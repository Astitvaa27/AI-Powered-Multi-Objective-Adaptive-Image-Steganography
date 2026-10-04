import { useId, useState, type ReactNode } from "react";
import { HelpCircle } from "lucide-react";
import { cn } from "@/lib/cn";

/**
 * Small "?" button that explains a term. Opens on hover, focus or tap,
 * and the text is exposed to screen readers via aria-describedby.
 */
export function InfoTip({
  children,
  label = "More information",
  className,
}: {
  children: ReactNode;
  label?: string;
  className?: string;
}) {
  const id = useId();
  const [open, setOpen] = useState(false);

  return (
    <span className={cn("relative inline-flex align-middle", className)}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={id}
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(event) => {
          if (event.key === "Escape") setOpen(false);
        }}
        className="rounded-full text-faint transition-colors hover:text-fg"
      >
        <HelpCircle className="h-3.5 w-3.5" aria-hidden />
      </button>
      <span
        id={id}
        role="tooltip"
        className={cn(
          "absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-lg border border-line bg-surface px-3 py-2 text-left text-xs font-normal normal-case leading-relaxed tracking-normal text-muted shadow-raised",
          open ? "block animate-fade-in" : "sr-only",
        )}
      >
        {children}
      </span>
    </span>
  );
}
