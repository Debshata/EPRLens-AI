import { AlertOctagon, Inbox } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toApiClientError } from "@/lib/errors";

export function LoadingState({ label = "Loading", rows = 3 }: { label?: string; rows?: number }) {
  return (
    <div role="status" aria-live="polite" className="space-y-3">
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-14 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
  icon,
}: {
  title: string;
  description: string;
  action?: { label: string; href?: string; onClick?: () => void };
  icon?: ReactNode;
}) {
  return (
    <Card variant="standard" className="flex flex-col items-center gap-3 py-12 text-center">
      <div className="text-muted">{icon ?? <Inbox className="size-8" aria-hidden />}</div>
      <h3 className="font-heading text-lg font-semibold">{title}</h3>
      <p className="max-w-md text-sm text-muted">{description}</p>
      {action &&
        (action.href ? (
          <Button asChild className="mt-2">
            <Link href={action.href}>{action.label}</Link>
          </Button>
        ) : (
          <Button className="mt-2" onClick={action.onClick}>
            {action.label}
          </Button>
        ))}
    </Card>
  );
}

/** Errors always say what happened AND what the user can do next. */
export function ErrorState({ error, onRetry, title = "This section could not load" }: { error: unknown; onRetry?: () => void; title?: string }) {
  const e = toApiClientError(error);
  return (
    <Card variant="alert" role="alert" className="flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <AlertOctagon className="mt-0.5 size-5 shrink-0 text-danger" aria-hidden />
        <div>
          <h3 className="font-heading font-semibold">{title}</h3>
          <p className="mt-1 text-sm text-fg/90">{e.message}</p>
          <p className="mt-1 text-sm text-muted">
            <span className="font-medium text-fg">What you can do: </span>
            {e.next_step}
          </p>
        </div>
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" className="self-start" onClick={onRetry}>
          Retry
        </Button>
      )}
    </Card>
  );
}
