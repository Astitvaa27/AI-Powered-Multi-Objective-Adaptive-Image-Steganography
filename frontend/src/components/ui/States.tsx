import type { ReactNode } from "react";
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
  steps,
  activeStep,
  className,
}: {
  label?: string;
  steps?: string[];
  activeStep?: number;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 px-6 py-12 text-center",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <Spinner className="h-6 w-6" />
      <p className="text-sm font-medium text-fg">{label}</p>

      {steps && steps.length > 0 && (
        <ol className="w-full max-w-xs space-y-1.5 text-left">
          {steps.map((step, index) => {
            const done = activeStep !== undefined && index < activeStep;
            const current = activeStep === index;

            return (
              <li
                key={step}
                className={cn(
                  "flex items-center gap-2 text-xs transition-colors",
                  done && "text-clean",
                  current && "text-fg",
                  !done && !current && "text-faint",
                )}
              >
                <span
                  className={cn(
                    "h-1.5 w-1.5 shrink-0 rounded-full",
                    done && "bg-clean",
                    current && "animate-pulse bg-accent",
                    !done && !current && "bg-line",
                  )}
                />
                {step}
              </li>
            );
          })}
        </ol>
      )}
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
  description?: string;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 px-6 py-14 text-center",
        className,
      )}
    >
      {icon && (
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-elevated text-faint">
          {icon}
        </span>
      )}
      <div>
        <p className="text-sm font-medium text-fg">{title}</p>
        {description && (
          <p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-muted">
            {description}
          </p>
        )}
      </div>
      {action}
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
        "flex flex-col items-center justify-center gap-3 px-6 py-12 text-center",
        className,
      )}
      role="alert"
    >
      <span className="flex h-11 w-11 items-center justify-center rounded-full bg-stego/10 text-stego">
        <AlertCircle className="h-5 w-5" />
      </span>
      <div>
        <p className="text-sm font-medium text-fg">{title}</p>
        <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-muted">
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
    <div className="space-y-2 p-5">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="skeleton h-10 w-full" />
      ))}
    </div>
  );
}
