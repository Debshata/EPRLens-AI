"use client";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import * as React from "react";
import { cn } from "@/lib/utils";

export const Tabs = TabsPrimitive.Root;

export function TabsList({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.List>) {
  return <TabsPrimitive.List className={cn("inline-flex w-full gap-1 overflow-x-auto rounded-full border border-white/10 bg-surface p-1 sm:w-auto", className)} {...props} />;
}
export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof TabsPrimitive.Trigger>) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "min-h-10 flex-1 whitespace-nowrap rounded-full px-4 text-sm font-medium text-muted transition-colors hover:text-fg data-[state=active]:bg-brand/15 data-[state=active]:text-brand-bright sm:flex-none",
        className,
      )}
      {...props}
    />
  );
}
export const TabsContent = TabsPrimitive.Content;
