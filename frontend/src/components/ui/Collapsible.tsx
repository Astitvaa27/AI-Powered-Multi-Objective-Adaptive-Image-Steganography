import { useId, useState, type ReactNode } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/cn";

export function Collapsible({
  title,
  description,
  badge,
  defaultOpen = false,
  children,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  badge?: ReactNode;
  defaultOpen?: boolean;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const panelId = useId();

  return (
    <div className={cn("border-b border-line last:border-b-0", className)}>
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={panelId}
        className="flex w-full items-center justify-between gap-3 px-5 py-3.5 text-left transition-colors hover:bg-elevated/60"
      >
        <span className="min-w-0">
          <span className="flex items-center gap-2">
            <span className="text-sm font-medium text-fg">{title}</span>
            {badge}
          </span>
          {description && (
            <span className="mt-0.5 block text-xs leading-relaxed text-muted">
              {description}
            </span>
          )}
        </span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-faint transition-transform duration-200",
            open && "rotate-180",
          )}
          aria-hidden
        />
      </button>

      {open && (
        <div id={panelId} className="animate-fade-up px-5 pb-5">
          {children}
        </div>
      )}
    </div>
  );
}
