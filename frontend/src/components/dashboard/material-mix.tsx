import { Badge } from "@/components/ui/badge";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { formatKg, formatPct, formatTonnes } from "@/lib/formatters";
import { MATERIAL_COLORS } from "@/lib/tokens";

export function MaterialMix({ mix, fy }: { mix: Record<string, number>; fy: string }) {
  const entries = Object.entries(mix).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((s, [, v]) => s + v, 0);
  return (
    <Card variant="standard" className="space-y-4" data-testid="material-mix">
      <div className="flex items-start justify-between gap-2">
        <div>
          <CardTitle>Material mix · {fy}</CardTitle>
          <CardDescription>Packaging placed on the market, by material (company records).</CardDescription>
        </div>
        <Badge variant="declared">Declared</Badge>
      </div>
      <ul className="space-y-3">
        {entries.map(([m, kg]) => (
          <li key={m}>
            <div className="mb-1 flex items-baseline justify-between gap-2 text-sm">
              <span className="font-medium">{m}</span>
              <span className="num text-xs text-muted">{formatKg(kg)} · {formatTonnes(kg)} · {formatPct((kg / total) * 100)}</span>
            </div>
            <div className="h-2 rounded-full bg-white/10" aria-hidden><div className="h-full rounded-full" style={{ width: `${(kg / total) * 100}%`, background: MATERIAL_COLORS[m] ?? "#94a3b8" }} /></div>
          </li>
        ))}
      </ul>
      <p className="num border-t border-white/10 pt-3 text-sm">Total <span className="font-semibold">{formatKg(total)}</span> <span className="text-muted">({formatTonnes(total)})</span></p>
      <p className="text-xs text-muted">Only plastic materials (PET, HDPE, PP) carry a current packaging-EPR regime in the handbook; other materials are shown for completeness, not as obligations.</p>
    </Card>
  );
}
