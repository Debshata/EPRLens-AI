import type { ReactNode } from "react";
import { SyntheticDataBadge } from "@/components/data/synthetic-data-badge";

export function PageHeader({ kicker, title, description, actions, synthetic = true }: { kicker?: string; title: string; description?: string; actions?: ReactNode; synthetic?: boolean }) {
  return (
    <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div className="max-w-2xl">
        {kicker && <p className="mb-2 font-mono text-xs uppercase tracking-widest text-brand-bright">{kicker}</p>}
        <h1 className="font-heading text-3xl font-bold tracking-tight md:text-4xl">{title}</h1>
        {description && <p className="mt-2 text-muted">{description}</p>}
        {synthetic && <SyntheticDataBadge className="mt-3" />}
      </div>
      {actions && <div className="flex flex-wrap gap-3">{actions}</div>}
    </header>
  );
}
