import { Info } from "lucide-react";
import { DISCLAIMER_SHORT } from "@/lib/config";

export function Disclaimer({ children = DISCLAIMER_SHORT }: { children?: React.ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-xs text-muted">
      <Info className="mt-0.5 size-3.5 shrink-0" aria-hidden />
      <span>{children}</span>
    </p>
  );
}
