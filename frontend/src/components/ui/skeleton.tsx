import { cn } from "@/lib/utils";

/** Static (non-shimmering) placeholder — respects reduced motion by never animating. */
export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("rounded-lg bg-white/[0.06]", className)} />;
}
