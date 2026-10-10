import { FlaskConical } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { SYNTHETIC_LABEL } from "@/lib/config";

/** Always shown wherever fixture/demo data is displayed (UX rule: label demo data as Synthetic demo data). */
export function SyntheticDataBadge({ className }: { className?: string }) {
  return (
    <Badge variant="synthetic" className={className} title="Generated test data about fictitious companies — not real records.">
      <FlaskConical className="size-3" aria-hidden />
      {SYNTHETIC_LABEL}
    </Badge>
  );
}
