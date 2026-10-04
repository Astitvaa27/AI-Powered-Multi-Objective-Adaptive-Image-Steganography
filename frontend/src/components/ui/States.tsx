import { useEffect, useState, type ReactNode } from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "./Button";

export function Spinner({ className }: { className?: string }) {
  return (
    <Loader2
      className={cn("h-4 w-4 animate-spin text-accent", className)}
      aria-hidden
    />
  );
}

export function LoadingState({
  label = "Loading…",
  className,
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <Spinner className="h-6 w-6" />
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}

/**
 * Feedback for a long single request. The backend does not stream
 * progress, so this shows elapsed time and what the server is doing
 * without pretending to know which stage is currently running.
 */
export function WorkingState({
  title,
  description,
  stages,
  className,
}: {
  title: string;
  description?: string;
  stages?: string[];
  className?: string;
}) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const started = Date.now();
    const timer = window.setInterval(
      () => setElapsed(Math.floor((Date.now() - started) / 1000)),
      1000,
    );
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div
      className={cn("px-6 py-8", className)}
      role="status"
      aria-live="polite"
      aria-busy="true"
    >
      <div className="mx-auto max-w-md">
        <div className="flex items-center justify-between gap-3">
          <p className="flex items-center gap-2 text-sm font-semibold text-fg">
            <Spinner />
            {title}
          </p>
          <span className="font-mono text-xs tabular-nums text-muted">
            {elapsed}s
          </span>
        </div>
        <div className="progress-indeterminate mt-3" />
        {description && (
          <p className="mt-3 text-xs leading-relaxed text-muted">{description}</p>
        )}
        {stages && stages.length > 0 && (
          <ul className="mt-4 space-y-1.5">
            {stages.map((stage) => (
              <li key={stage} className="flex items-start gap-2 text-xs text-muted">
                <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-faint" />
                {stage}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className,
}: {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
    >
      {icon && (
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-elevated text-muted">
          {icon}
        </span>
      )}
      <div>
        <p className="text-sm font-semibold text-fg">{title}</p>
        {description && (
          <p className="mx-auto mt-1 max-w-sm text-sm leading-relaxed text-muted">
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-1">{action}</div>}
    </div>
  );
}

export function ErrorState({
  title = "Something went wrong",
  message,
  onRetry,
  className,
}: {
  title?: string;
  message: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-10 text-center",
        className,
      )}
      role="alert"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-stego/10 text-stego">
        <AlertCircle className="h-5 w-5" />
      </span>
      <div>
        <p className="text-sm font-semibold text-fg">{title}</p>
        <p className="mx-auto mt-1 max-w-md text-sm leading-relaxed text-muted">
          {message}
        </p>
      </div>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          <RefreshCw className="h-3.5 w-3.5" />
          Try again
        </Button>
      )}
    </div>
  );
}

export function SkeletonRows({ rows = 4 }: { rows?: number }) {
  return (
    <div className="space-y-2 p-5" aria-hidden>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton h-10 w-full" />
      ))}
    </div>
  );
}
