import { useEffect, useRef, useState, type ReactNode } from "react";
import { Link, NavLink, useLocation } from "react-router-dom";
import {
  ArrowLeft,
  History,
  KeyRound,
  LayoutGrid,
  LockKeyhole,
  LogOut,
  Menu,
  Moon,
  ScanSearch,
  Settings,
  Sun,
  X,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useTheme } from "@/context/ThemeContext";
import { usePageTitle } from "@/hooks/usePageTitle";
import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/Button";
import { Logo } from "./Logo";

export const NAV_SECTIONS = [
  {
    label: null,
    items: [{ to: "/", label: "Dashboard", icon: LayoutGrid }],
  },
  {
    label: "Tools",
    items: [
      { to: "/hide", label: "Hide a Message", icon: LockKeyhole },
      { to: "/extract", label: "Extract a Message", icon: KeyRound },
      { to: "/analyze", label: "Analyze an Image", icon: ScanSearch },
    ],
  },
  {
    label: "Records",
    items: [{ to: "/history", label: "History", icon: History }],
  },
] as const;

function NavItem({
  to,
  label,
  icon: Icon,
}: {
  to: string;
  label: string;
  icon: typeof LayoutGrid;
}) {
  return (
    <NavLink
      to={to}
      end={to === "/"}
      className={({ isActive }) =>
        cn(
          "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-accent-soft text-accent"
            : "text-muted hover:bg-elevated hover:text-fg",
        )
      }
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {label}
    </NavLink>
  );
}

function SidebarContent() {
  const { profile, signOut } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-16 shrink-0 items-center px-5">
        <Link to="/" aria-label="StegoLab home" className="rounded-lg">
          <Logo />
        </Link>
      </div>

      <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4" aria-label="Main">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label ?? "home"}>
            {section.label && (
              <p className="mb-1.5 px-3 text-xs font-medium text-faint">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavItem key={item.to} {...item} />
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="shrink-0 space-y-0.5 border-t border-line px-3 py-3">
        <NavItem to="/settings" label="Settings" icon={Settings} />
        <button
          type="button"
          onClick={toggleTheme}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-muted transition-colors hover:bg-elevated hover:text-fg"
        >
          {theme === "dark" ? (
            <Sun className="h-4 w-4" aria-hidden />
          ) : (
            <Moon className="h-4 w-4" aria-hidden />
          )}
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </div>

      <div className="shrink-0 border-t border-line p-3">
        <div className="flex items-center gap-3 rounded-lg px-2 py-1.5">
          <span
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-elevated text-xs font-semibold uppercase text-muted"
            aria-hidden
          >
            {profile?.email?.charAt(0) ?? "·"}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-medium text-fg" title={profile?.email}>
              {profile?.email ?? "Signed in"}
            </span>
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={signOut}
            aria-label="Sign out"
            title="Sign out"
            className="h-8 w-8"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export function AppLayout({
  title,
  pageTitle,
  description,
  actions,
  back,
  children,
}: {
  title: string;
  /** Browser tab title, if it should differ from the heading. */
  pageTitle?: string;
  description?: ReactNode;
  actions?: ReactNode;
  /** Optional back link shown above the title. */
  back?: { to: string; label: string };
  children: ReactNode;
}) {
  usePageTitle(pageTitle ?? title);

  const location = useLocation();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);
  const mainRef = useRef<HTMLElement>(null);

  // Close the mobile drawer on navigation and reset scroll for the new page.
  useEffect(() => {
    setDrawerOpen(false);
    mainRef.current?.scrollTo({ top: 0 });
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;

    const previous = document.activeElement as HTMLElement | null;
    const menuButton = menuButtonRef.current;
    drawerRef.current?.querySelector<HTMLElement>("a, button")?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      (previous ?? menuButton)?.focus();
    };
  }, [drawerOpen]);

  return (
    <div className="flex h-full w-full overflow-hidden bg-bg">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded-lg focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:shadow-raised"
      >
        Skip to content
      </a>

      <aside className="hidden w-64 shrink-0 border-r border-line bg-surface lg:block">
        <SidebarContent />
      </aside>

      {drawerOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Navigation">
          <div
            className="absolute inset-0 animate-fade-in bg-black/50"
            onClick={() => setDrawerOpen(false)}
            aria-hidden
          />
          <div
            ref={drawerRef}
            className="absolute inset-y-0 left-0 w-72 max-w-[85vw] animate-slide-in-left border-r border-line bg-surface shadow-overlay"
          >
            <button
              type="button"
              onClick={() => setDrawerOpen(false)}
              aria-label="Close navigation"
              className="absolute right-3 top-4 z-10 rounded-lg p-2 text-muted hover:bg-elevated hover:text-fg"
            >
              <X className="h-4 w-4" />
            </button>
            <SidebarContent />
          </div>
        </div>
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-line bg-surface px-4 lg:hidden">
          <button
            ref={menuButtonRef}
            type="button"
            onClick={() => setDrawerOpen(true)}
            aria-label="Open navigation"
            aria-expanded={drawerOpen}
            className="rounded-lg p-2 text-muted transition-colors hover:bg-elevated hover:text-fg"
          >
            <Menu className="h-5 w-5" />
          </button>
          <Link to="/" aria-label="StegoLab home" className="rounded-lg">
            <Logo />
          </Link>
          <span className="w-9" aria-hidden />
        </header>

        <main
          id="main-content"
          ref={mainRef}
          tabIndex={-1}
          className="min-h-0 flex-1 overflow-y-auto focus:outline-none"
        >
          <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
            <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
              <div className="min-w-0">
                {back && (
                  <Link
                    to={back.to}
                    className="mb-2 inline-flex items-center gap-1.5 rounded text-sm text-muted transition-colors hover:text-fg"
                  >
                    <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
                    {back.label}
                  </Link>
                )}
                <h1 className="text-2xl font-semibold tracking-tight text-fg">
                  {title}
                </h1>
                {description && (
                  <p className="mt-1 max-w-2xl text-sm leading-relaxed text-muted">
                    {description}
                  </p>
                )}
              </div>
              {actions && (
                <div className="flex flex-wrap items-center gap-2">{actions}</div>
              )}
            </div>
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
