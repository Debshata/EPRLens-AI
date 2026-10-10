import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const cardVariants = cva("rounded-2xl border", {
  variants: {
    variant: {
      standard: "border-white/10 bg-surface",
      glass: "border-white/10 bg-white/[0.04] backdrop-blur-lg",
      metric: "border-white/10 bg-surface p-5",
      compact: "border-white/10 bg-surface p-4",
      alert: "border-danger/40 bg-danger/5",
      caution: "border-caution/40 bg-caution/5",
    },
    padded: { true: "p-6 md:p-7", false: "" },
  },
  defaultVariants: { variant: "standard", padded: true },
});

export interface CardProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

export function Card({ className, variant, padded, ...props }: CardProps) {
  const pad = variant === "metric" || variant === "compact" ? false : padded;
  return <div className={cn(cardVariants({ variant, padded: pad }), className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return <h3 className={cn("font-heading text-lg font-semibold tracking-tight text-fg", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-muted", className)} {...props} />;
}
