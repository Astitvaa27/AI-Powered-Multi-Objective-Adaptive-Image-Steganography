import type { ReactNode } from "react";
import { KeyRound, LockKeyhole, Moon, ScanSearch, Sun } from "lucide-react";
import { useTheme } from "@/context/ThemeContext";
import { usePageTitle } from "@/hooks/usePageTitle";
import { Button } from "@/components/ui/Button";
import { Logo } from "./Logo";

const CAPABILITIES = [
  {
    icon: LockKeyhole,
    title: "Hide a message",
    text: "StegoLab tries several hiding methods and keeps the one that is hardest to notice.",
  },
  {
    icon: KeyRound,
    title: "Extract a message",
    text: "Recover hidden text from images you created — the method is remembered for you.",
  },
  {
    icon: ScanSearch,
    title: "Analyze an image",
    text: "Check whether an image is likely to contain hidden data, with an explained report.",
  },
];

/** Shared frame for every signed-out screen. */
export function AuthLayout({
  pageTitle,
  icon,
  title,
  description,
  children,
  footer,
}: {
  pageTitle: string;
  /** Optional icon shown above the heading (e.g. on status screens). */
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  usePageTitle(pageTitle);
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-full w-full">
      <aside className="relative hidden w-[44%] max-w-xl flex-col justify-between overflow-hidden border-r border-line bg-surface p-12 lg:flex">
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.5]"
          style={{
            backgroundImage:
              "linear-gradient(rgb(var(--line) / 0.6) 1px, transparent 1px), linear-gradient(90deg, rgb(var(--line) / 0.6) 1px, transparent 1px)",
            backgroundSize: "32px 32px",
            maskImage: "radial-gradient(ellipse at 30% 40%, black, transparent 75%)",
            WebkitMaskImage:
              "radial-gradient(ellipse at 30% 40%, black, transparent 75%)",
          }}
          aria-hidden
        />

        <Logo size="lg" className="relative" />

        <div className="relative">
          <p className="text-3xl font-semibold leading-tight tracking-tight text-fg">
            Hide, find and detect messages inside images.
          </p>

          <ul className="mt-10 space-y-6">
            {CAPABILITIES.map(({ icon: Icon, title: itemTitle, text }) => (
              <li key={itemTitle} className="flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-soft text-accent">
                  <Icon className="h-4 w-4" aria-hidden />
                </span>
                <span>
                  <span className="block text-sm font-semibold text-fg">{itemTitle}</span>
                  <span className="mt-0.5 block text-sm leading-relaxed text-muted">
                    {text}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="relative text-xs leading-relaxed text-faint">
          Detection results are statistical estimates, not proof.
        </p>
      </aside>

      <div className="relative flex flex-1 flex-col">
        <div className="flex items-center justify-between px-5 py-4 lg:justify-end">
          <Logo className="lg:hidden" />
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>

        <main className="flex flex-1 items-start justify-center px-5 pb-12 pt-4 sm:items-center sm:pt-0">
          <div className="w-full max-w-sm">
            {icon && (
              <span className="mb-5 flex h-12 w-12 items-center justify-center rounded-xl bg-accent-soft text-accent">
                {icon}
              </span>
            )}

            <h1 className="text-2xl font-semibold tracking-tight text-fg">{title}</h1>
            {description && (
              <p className="mt-1.5 text-sm leading-relaxed text-muted">{description}</p>
            )}

            <div className="mt-7">{children}</div>

            {footer && (
              <div className="mt-8 border-t border-line pt-5 text-center text-sm text-muted">
                {footer}
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
