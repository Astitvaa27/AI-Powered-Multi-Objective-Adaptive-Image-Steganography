import { NavLink } from "react-router-dom";
import {
  FileBarChart2,
  LayoutDashboard,
  Radar,
  Settings,
  ShieldHalf,
  X,
} from "lucide-react";
import { cn } from "@/lib/cn";

export const NAV_ITEMS = [
  {
    to: "/",
    label: "Dashboard",
    icon: LayoutDashboard,
    description: "Overview and activity",
  },
  {
    to: "/steganography",
    label: "Steganography",
    icon: ShieldHalf,
    description: "Embed and extract payloads",
  },
  {
    to: "/steganalysis",
    label: "Steganalysis",
    icon: Radar,
    description: "Detect hidden data",
  },
  {
    to: "/reports",
    label: "Reports",
    icon: FileBarChart2,
    description: "Analysis history",
  },
  {
    to: "/settings",
    label: "Settings",
    icon: Settings,
    description: "Theme and system status",
  },
] as const;

export function Sidebar({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden
        />
      )}

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-line bg-surface transition-transform duration-200 lg:static lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Primary navigation"
      >
        <div className="flex h-16 shrink-0 items-center justify-between gap-2 border-b border-line px-5">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-accent text-white dark:text-[rgb(var(--bg))]">
              <Radar className="h-4 w-4" />
            </span>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-tight text-fg">
                StegoLab
              </p>
              <p className="text-[10px] uppercase tracking-widest text-faint">
                Forensics suite
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="rounded p-1 text-faint hover:text-fg lg:hidden"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto p-3">
          {NAV_ITEMS.map(({ to, label, icon: Icon, description }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={onClose}
              className={({ isActive }) =>
                cn(
                  "flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors",
                  isActive
                    ? "bg-accent-soft text-accent"
                    : "text-muted hover:bg-elevated hover:text-fg",
                )
              }
            >
              <Icon className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
              <span className="min-w-0">
                <span className="block text-sm font-medium">{label}</span>
                <span className="block text-[11px] leading-tight opacity-70">
                  {description}
                </span>
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="shrink-0 border-t border-line p-4">
          <p className="text-[10px] leading-relaxed text-faint">
            Multi-Objective Adaptive Image Steganography &amp; Steganalysis
            Framework
          </p>
        </div>
      </aside>
    </>
  );
}
