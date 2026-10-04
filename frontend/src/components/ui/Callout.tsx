import type { ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, XCircle } from "lucide-react";
import { cn } from "@/lib/cn";

type CalloutTone = "info" | "success" | "warning" | "danger";

const STYLES: Record<CalloutTone, { box: string; icon: string; Icon: typeof Info }> = {
  info: { box: "border-accent/25 bg-accent-soft/60", icon: "text-accent", Icon: Info },
  success: { box: "border-clean/30 bg-clean/10", icon: "text-clean", Icon: CheckCircle2 },
  warning: { box: "border-warn/30 bg-warn/10", icon: "text-warn", Icon: AlertTriangle },
  danger: { box: "border-stego/30 bg-stego/10", icon: "text-stego", Icon: XCircle },
};

/** Inline message box for guidance, warnings and outcomes. */
export function Callout({
  tone = "info",
  title,
  children,
  className,
  role,
}: {
  tone?: CalloutTone;
  title?: ReactNode;
  children?: ReactNode;
  className?: string;
  role?: "status" | "alert";
}) {
  const { box, icon, Icon } = STYLES[tone];

  return (
    <div
      className={cn("flex items-start gap-3 rounded-lg border px-4 py-3", box, className)}
      role={role}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", icon)} aria-hidden />
      <div className="min-w-0 text-sm leading-relaxed text-fg">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && "mt-0.5", "text-muted")}>{children}</div>}
      </div>
    </div>
  );
}
