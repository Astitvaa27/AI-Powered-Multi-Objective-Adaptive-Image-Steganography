import { useRef, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";

interface TabOption<T extends string> {
  value: T;
  label: ReactNode;
  icon?: ReactNode;
  disabled?: boolean;
}

/** Arrow-key navigation shared by the tab-like controls below. */
function useRovingFocus<T extends string>(
  options: TabOption<T>[],
  value: T,
  onChange: (value: T) => void,
) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const onKeyDown = (event: KeyboardEvent) => {
    const enabled = options.filter((option) => !option.disabled);
    const index = enabled.findIndex((option) => option.value === value);
    let next = -1;

    if (event.key === "ArrowRight" || event.key === "ArrowDown") next = index + 1;
    if (event.key === "ArrowLeft" || event.key === "ArrowUp") next = index - 1;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = enabled.length - 1;
    if (next === -1 && !["Home", "End"].includes(event.key)) return;

    event.preventDefault();
    const target = enabled[(next + enabled.length) % enabled.length];
    onChange(target.value);
    refs.current[options.indexOf(target)]?.focus();
  };

  return { refs, onKeyDown };
}

/** Underlined tabs for switching between views of the same content. */
export function Tabs<T extends string>({
  value,
  options,
  onChange,
  label,
  className,
}: {
  value: T;
  options: TabOption<T>[];
  onChange: (value: T) => void;
  label: string;
  className?: string;
}) {
  const { refs, onKeyDown } = useRovingFocus(options, value, onChange);

  return (
    <div
      role="tablist"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn("flex gap-1 overflow-x-auto border-b border-line", className)}
    >
      {options.map((option, index) => (
        <button
          key={option.value}
          ref={(element) => {
            refs.current[index] = element;
          }}
          type="button"
          role="tab"
          aria-selected={value === option.value}
          tabIndex={value === option.value ? 0 : -1}
          disabled={option.disabled}
          onClick={() => onChange(option.value)}
          className={cn(
            "-mb-px flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors disabled:opacity-50",
            value === option.value
              ? "border-accent text-fg"
              : "border-transparent text-muted hover:text-fg",
          )}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}

/** Pill-style choice between a few mutually exclusive options. */
export function SegmentedControl<T extends string>({
  value,
  options,
  onChange,
  label,
  className,
}: {
  value: T;
  options: TabOption<T>[];
  onChange: (value: T) => void;
  label: string;
  className?: string;
}) {
  const { refs, onKeyDown } = useRovingFocus(options, value, onChange);

  return (
    <div
      role="radiogroup"
      aria-label={label}
      onKeyDown={onKeyDown}
      className={cn("inline-flex gap-1 rounded-lg bg-elevated p-1", className)}
    >
      {options.map((option, index) => (
        <button
          key={option.value}
          ref={(element) => {
            refs.current[index] = element;
          }}
          type="button"
          role="radio"
          aria-checked={value === option.value}
          tabIndex={value === option.value ? 0 : -1}
          disabled={option.disabled}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex flex-1 items-center justify-center gap-1.5 whitespace-nowrap rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50",
            value === option.value
              ? "bg-surface text-fg shadow-sm"
              : "text-muted hover:text-fg",
          )}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}
