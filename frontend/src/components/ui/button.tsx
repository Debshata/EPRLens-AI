import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { Loader2 } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

export const buttonVariants = cva(
  "inline-flex min-h-11 select-none items-center justify-center gap-2 whitespace-nowrap rounded-full px-5 text-sm font-semibold uppercase tracking-wider transition-all duration-200 disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary:
          "bg-gradient-to-r from-brand-dark to-brand text-bg shadow-glow-sm hover:shadow-glow hover:brightness-110",
        outline: "border-2 border-white/20 bg-transparent text-fg hover:border-white/60 hover:bg-white/10",
        ghost: "bg-transparent text-fg hover:bg-white/10 hover:text-brand-bright",
        danger: "border border-danger/60 bg-danger/10 text-danger hover:bg-danger/20",
        text: "min-h-0 rounded-md px-1 normal-case tracking-normal text-brand-bright underline-offset-4 hover:underline",
      },
      size: { md: "", sm: "min-h-9 px-4 text-xs", icon: "size-11 min-h-11 px-0" },
    },
    defaultVariants: { variant: "primary", size: "md" },
  },
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  loading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant, size, asChild, loading, disabled, children, ...props },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {asChild ? (
        children
      ) : (
        <>
          {loading && <Loader2 className="animate-spin" aria-hidden />}
          {children}
        </>
      )}
    </Comp>
  );
});
