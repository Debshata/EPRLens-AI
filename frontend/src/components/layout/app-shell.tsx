"use client";

import { BarChart3, FlaskConical, GitCompareArrows, Layers, Menu, RotateCcw, SlidersHorizontal, UploadCloud } from "lucide-react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useState, type ReactNode } from "react";
import { EmptyState, LoadingState } from "@/components/data/data-state";
import { SyntheticDataBadge } from "@/components/data/synthetic-data-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { useApp } from "@/lib/app-state";
import { API_MODE } from "@/lib/config";
import { cn } from "@/lib/utils";

const NAV = [
  { group: "Workspace", items: [
    { href: "/app/dashboard", label: "Dashboard", icon: BarChart3 },
    { href: "/app/workspace", label: "Evidence", icon: UploadCloud },
    { href: "/app/review", label: "Findings", icon: GitCompareArrows },
  ] },
  { group: "Decisions", items: [{ href: "/app/simulator", label: "Simulator", icon: SlidersHorizontal }] },
] as const;

function NavList({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <nav aria-label="Primary" className="flex flex-col gap-6">
      {NAV.map((g) => (
        <div key={g.group}>
          <p className="mb-2 px-3 font-mono text-[11px] uppercase tracking-widest text-muted">{g.group}</p>
          <ul className="flex flex-col gap-1">
            {g.items.map(({ href, label, icon: Icon }) => {
              const active = pathname === href;
              return (
                <li key={href}>
                  <Link
                    href={href}
                    onClick={onNavigate}
                    aria-current={active ? "page" : undefined}
                    className={cn(
                      "flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-medium transition-colors",
                      active ? "bg-brand/15 text-brand-bright" : "text-muted hover:bg-white/5 hover:text-fg",
                    )}
                  >
                    <Icon className="size-4" aria-hidden />
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </nav>
  );
}

function Brand() {
  return (
    <Link href="/" className="flex items-center gap-2 font-heading text-lg font-bold tracking-tight">
      <span className="grid size-8 place-items-center rounded-lg border border-brand/50 bg-brand/15 text-brand-bright">
        <Layers className="size-4" aria-hidden />
      </span>
      EPRLens<span className="text-brand-bright">.AI</span>
    </Link>
  );
}

/** The Findings deep link (/app/review?demo=1) may render before a company exists: that page loads the sample flow itself. */
function useDemoDeepLink(): boolean {
  const pathname = usePathname();
  const params = useSearchParams();
  return pathname === "/app/review" && params.get("demo") === "1";
}

function Gate({ children }: { children: ReactNode }) {
  const { company, hydrated } = useApp();
  const deepLink = useDemoDeepLink();
  if (!hydrated) return <LoadingState label="Loading workspace" />;
  if (!company && !deepLink) {
    return (
      <EmptyState
        title="No company yet"
        description="Set up a company (or open the synthetic demo company) to start reviewing packaging evidence. Nothing is shown until there is data."
        action={{ label: "Open demo company", href: "/onboarding?demo=1" }}
      />
    );
  }
  return <>{children}</>;
}

export function AppShell({ children }: { children: ReactNode }) {
  const { company, resetDemo } = useApp();
  const [drawer, setDrawer] = useState(false);

  return (
    <div className="min-h-screen bg-bg">
      {/* desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-[248px] flex-col gap-8 border-r border-white/10 bg-surface p-5 lg:flex">
        <Brand />
        <NavList />
        <div className="mt-auto space-y-3">
          <Button variant="ghost" size="sm" className="w-full justify-start normal-case tracking-normal" onClick={() => { if (window.confirm("Clear the demo company, uploads and review history from this browser?")) resetDemo(); }}>
            <RotateCcw aria-hidden /> Reset demo
          </Button>
          <p className="text-[11px] leading-relaxed text-muted">Pre-compliance decision support. Not a CPCB filing, certification or legal advice.</p>
        </div>
      </aside>

      <div className="lg:pl-[248px]">
      {/* top bar */}
      <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-white/10 bg-bg/90 px-4 backdrop-blur lg:h-16 lg:px-8">
        <Button variant="ghost" size="icon" className="lg:hidden" aria-label="Open navigation" onClick={() => setDrawer(true)}>
          <Menu />
        </Button>
        <div className="min-w-0 flex-1">
          <p className="truncate font-heading text-sm font-semibold">{company?.company.company_name ?? "EPRLens AI"}</p>
          {company && <p className="num truncate text-[11px] text-muted">{company.company.company_id} · FY 2025-26</p>}
        </div>
        <SyntheticDataBadge className="hidden sm:inline-flex" />
        <span className="hidden items-center gap-1.5 rounded-full border border-white/15 px-2.5 py-1 font-mono text-[11px] uppercase tracking-wider text-muted md:inline-flex" title={API_MODE === "mock" ? "Fixtures only — no backend calls." : "Calling the live backend through /api/*."}>
          <FlaskConical className="size-3" aria-hidden /> {API_MODE} mode
        </span>
      </header>

      <Dialog open={drawer} onOpenChange={setDrawer}>
        <DialogContent side="left" className="flex flex-col gap-8">
          <DialogTitle className="sr-only">Navigation</DialogTitle>
          <DialogDescription className="sr-only">Main navigation links</DialogDescription>
          <Brand />
          <NavList onNavigate={() => setDrawer(false)} />
        </DialogContent>
      </Dialog>

      <main id="main" className="mx-auto w-full max-w-[1280px] px-4 py-8 lg:px-8">
        <Suspense fallback={<LoadingState label="Loading" />}>
          <Gate>{children}</Gate>
        </Suspense>
      </main>
      </div>
    </div>
  );
}
