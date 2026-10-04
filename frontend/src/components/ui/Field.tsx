import {
  cloneElement,
  forwardRef,
  isValidElement,
  useId,
  type InputHTMLAttributes,
  type ReactElement,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { AlertCircle } from "lucide-react";
import { cn } from "@/lib/cn";

const CONTROL =
  "w-full rounded-lg border border-line-strong bg-surface px-3 text-sm text-fg shadow-sm placeholder:text-faint transition-colors hover:border-faint focus:border-accent focus-visible:ring-2 focus-visible:ring-accent/30 focus-visible:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-60 aria-[invalid=true]:border-stego";

export function Label({
  htmlFor,
  children,
  hint,
  className,
}: {
  htmlFor: string;
  children: ReactNode;
  hint?: ReactNode;
  className?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className={cn(
        "mb-1.5 flex items-baseline justify-between gap-2 text-sm font-medium text-fg",
        className,
      )}
    >
      <span>{children}</span>
      {hint && <span className="text-xs font-normal text-faint">{hint}</span>}
    </label>
  );
}

export function HelpText({
  id,
  children,
  className,
}: {
  id?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <p id={id} className={cn("mt-1.5 text-xs leading-relaxed text-muted", className)}>
      {children}
    </p>
  );
}

export function FieldError({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="mt-1.5 flex items-start gap-1.5 text-xs text-stego" role="alert">
      <AlertCircle className="mt-px h-3.5 w-3.5 shrink-0" aria-hidden />
      <span>{children}</span>
    </p>
  );
}

/**
 * Label + control + help text + inline error, wired together for screen
 * readers via aria-describedby / aria-invalid.
 */
export function Field({
  label,
  hint,
  help,
  error,
  children,
  className,
  labelAction,
}: {
  label: ReactNode;
  hint?: ReactNode;
  help?: ReactNode;
  error?: string | null;
  /** A single input/select/textarea element. */
  children: ReactElement;
  className?: string;
  /** Rendered at the right of the label row, e.g. a "Forgot password?" link. */
  labelAction?: ReactNode;
}) {
  const generatedId = useId();
  const controlId = (children.props as { id?: string }).id ?? generatedId;
  const helpId = help ? `${controlId}-help` : undefined;
  const errorId = error ? `${controlId}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;

  const control = isValidElement(children)
    ? cloneElement(children as ReactElement<Record<string, unknown>>, {
        id: controlId,
        "aria-describedby": describedBy,
        "aria-invalid": error ? true : undefined,
      })
    : children;

  return (
    <div className={className}>
      {labelAction ? (
        <div className="mb-1.5 flex items-baseline justify-between gap-2">
          <Label htmlFor={controlId} hint={hint} className="mb-0">
            {label}
          </Label>
          {labelAction}
        </div>
      ) : (
        <Label htmlFor={controlId} hint={hint}>
          {label}
        </Label>
      )}
      {control}
      {help && !error && <HelpText id={helpId}>{help}</HelpText>}
      {error && <FieldError id={errorId}>{error}</FieldError>}
    </div>
  );
}

export const Input = forwardRef<
  HTMLInputElement,
  InputHTMLAttributes<HTMLInputElement>
>(({ className, ...props }, ref) => (
  <input ref={ref} className={cn(CONTROL, "h-10", className)} {...props} />
));
Input.displayName = "Input";

export const Select = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(({ className, children, ...props }, ref) => (
  <select ref={ref} className={cn(CONTROL, "h-10 pr-8", className)} {...props}>
    {children}
  </select>
));
Select.displayName = "Select";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(CONTROL, "resize-y py-2.5 leading-relaxed", className)}
    {...props}
  />
));
Textarea.displayName = "Textarea";
