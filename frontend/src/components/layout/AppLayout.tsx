import { useState, type ReactNode } from "react";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppLayout({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
}) {
  const [navOpen, setNavOpen] = useState(false);

  return (
    <div className="flex h-full w-full overflow-hidden bg-bg">
      <Sidebar open={navOpen} onClose={() => setNavOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <Header
          title={title}
          subtitle={subtitle}
          onMenuClick={() => setNavOpen(true)}
        />
        {/* Full-bleed content area: pages own their own grid. */}
        <main className="min-h-0 flex-1 overflow-y-auto px-5 py-6 lg:px-8">
          {children}
        </main>
      </div>
    </div>
  );
}
