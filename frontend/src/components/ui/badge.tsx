import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

/**
 * Badge variants map to the UX-spec status vocabulary. Colour is never the only signal: every variant
 * also carries a text label and a distinct border style (solid / dashed / dotted).
 */
export const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-mono text-[11px] font-medium uppercase tracking-wider",
  {
    variants: {
      variant: {
        neutral: "border-white/15 bg-white/5 text-muted",
        synthetic: "border-brand/50 bg-brand/10 text-brand-bright",
        confirmed: "border-solid border-brand/60 bg-brand/10 text-brand-bright",
        declared: "border-solid border-info/50 bg-info/10 text-info",
        estimated: "border-dashed border-info/70 bg-info/5 text-info",
        needs_review: "border-solid border-caution/70 bg-caution/10 text-caution",
        unknown: "border-dotted border-white/30 bg-transparent text-muted",
        reviewed: "border-solid border-brand-bright/50 bg-transparent text-brand-bright",
        high: "border-danger/60 bg-danger/10 text-danger",
        medium: "border-caution/60 bg-caution/10 text-caution",
        low: "border-white/25 bg-white/5 text-fg",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}
