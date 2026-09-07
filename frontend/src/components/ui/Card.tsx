import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return <section className={cn("panel", className)}>{children}</section>;
}

interface CardHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export function CardHeader({
  title,
  description,
  icon,
  actions,
  className,
}: CardHeaderProps) {
  return (
    <header
      className={cn(
        "flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4",
        className,
      )}
    >
      <div className="flex min-w-0 items-start gap-3">
        {icon && <span className="mt-0.5 text-accent">{icon}</span>}
        <div className="min-w-0">
          <h2 className="truncate text-sm font-semibold tracking-tight text-fg">
            {title}
          </h2>
          {description && (
            <p className="mt-0.5 text-xs leading-relaxed text-muted">
              {description}
            </p>
          )}
        </div>
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </header>
  );
}

export function CardBody({ children, className }: CardProps) {
  return <div className={cn("p-5", className)}>{children}</div>;
}
