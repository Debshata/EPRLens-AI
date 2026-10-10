import type { ReactNode } from "react";
import { Card } from "@/components/ui/card";
import { EvidenceStatusBadge } from "@/components/data/status-badges";
import type { EvidenceStatus } from "@/lib/contracts";
import { formatKg, formatTonnes } from "@/lib/formatters";

export function MetricCard({
  label,
  value,
  hint,
  status,
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  status?: EvidenceStatus;
  icon?: ReactNode;
}) {
  return (
    <Card variant="metric" className="flex flex-col gap-2">
      <div className="flex items-center justify-between gap-2">
        <span className="font-mono text-[11px] uppercase tracking-wider text-muted">{label}</span>
        {icon && <span className="text-brand-bright">{icon}</span>}
      </div>
      <div className="num text-2xl font-semibold text-fg md:text-3xl">{value}</div>
      <div className="flex flex-wrap items-center gap-2 text-xs text-muted">
        {status && <EvidenceStatusBadge status={status} />}
        {hint}
      </div>
    </Card>
  );
}

/** "499,500 kg" with the tonne equivalent underneath when ≥ 1,000 kg. */
export function Mass({ kg, className }: { kg: number; className?: string }) {
  return (
    <span className={className}>
      <span className="num">{formatKg(kg)}</span>
      {Math.abs(kg) >= 1000 && <span className="num ml-2 text-muted">({formatTonnes(kg)})</span>}
    </span>
  );
}
