import Image from "next/image";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import { EvidenceStatusBadge } from "@/components/data/status-badges";
import type { ImageResult } from "@/lib/contracts";
import { formatPct } from "@/lib/formatters";

const LABEL: Record<ImageResult["predicted_class"], string> = {
  plastic: "Plastic", paper: "Paper", cardboard: "Cardboard", metal: "Metal", glass: "Glass", battery: "Battery", trash_other: "Other / mixed",
};

/** Probable material only — never an official EPR / legal category. */
export function MaterialPredictionCard({ result, previewSrc, fileName }: { result: ImageResult; previewSrc?: string | null; fileName?: string }) {
  const pct = Math.round(result.confidence * 100);
  return (
    <Card variant="standard" className="space-y-4" data-testid="material-prediction">
      <div className="flex items-start justify-between gap-3">
        <CardTitle>Probable material</CardTitle>
        <EvidenceStatusBadge status={result.uncertain ? "needs_review" : "estimated"} />
      </div>
      <div className="grid gap-4 sm:grid-cols-[160px_1fr]">
        {previewSrc ? (
          <Image src={previewSrc} alt={fileName ? `Uploaded packaging: ${fileName}` : "Uploaded packaging photo"} width={320} height={240} unoptimized className="h-auto w-full rounded-xl border border-white/10 object-cover" />
        ) : (
          <div className="grid h-32 place-items-center rounded-xl border border-dashed border-white/15 text-xs text-muted">No preview</div>
        )}
        <div className="space-y-3">
          <p className="font-heading text-3xl font-bold">
            {result.uncertain ? <>Uncertain: <span className="text-caution">{LABEL[result.predicted_class]}?</span></> : <span className="text-brand-bright">{LABEL[result.predicted_class]}</span>}
          </p>
          <div>
            <div className="mb-1 flex justify-between text-xs text-muted">
              <span>Model confidence</span>
              <span className="num text-fg">{formatPct(pct)}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10" role="meter" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} aria-label="Model confidence">
              <div className={result.uncertain ? "h-full bg-caution" : "h-full bg-brand"} style={{ width: `${pct}%` }} />
            </div>
          </div>
          {result.uncertain && (
            <p className="text-sm text-caution">Confidence is low, so this is not a reliable result. Please confirm the material yourself or upload a clearer photo.</p>
          )}
          <p className="text-xs text-muted">Model: <span className="num">{result.model_version}</span> · Probable material only — not an official EPR or legal category. Plastic category (I–IV) must be confirmed from product specifications.</p>
          <Badge variant="neutral">Demo output (image model not connected)</Badge>
        </div>
      </div>
    </Card>
  );
}
