"use client";

import { FileText, Image as ImageIcon, Table2, UploadCloud } from "lucide-react";
import { useId, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import type { UploadKind } from "@/lib/contracts";
import { UPLOAD_RULES } from "@/lib/upload-validation";
import { cn } from "@/lib/utils";
import type { AddFileOutcome } from "@/lib/app-state";

const ICON = { csv: Table2, invoice: FileText, image: ImageIcon } as const;

export interface SampleOption {
  id: string;
  label: string;
  path: string;
  file_name: string;
  mime: string;
}

export function UploadDropzone({
  kind,
  samples,
  onFile,
  busy,
}: {
  kind: UploadKind;
  samples: SampleOption[];
  onFile: (file: File, opts: { sample: boolean }) => Promise<AddFileOutcome>;
  busy?: boolean;
}) {
  const rule = UPLOAD_RULES[kind];
  const Icon = ICON[kind];
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "warn"; text: string; next: string } | null>(null);

  async function handle(file: File, sample: boolean) {
    setMessage(null);
    const out = await onFile(file, { sample });
    if (!out.ok) setMessage({ kind: "error", text: out.message ?? "The file could not be processed.", next: out.next_step ?? "Try again with another file." });
    else if (out.duplicateOf) setMessage({ kind: "warn", text: out.message ?? "Duplicate file.", next: out.next_step ?? "" });
  }

  async function loadSample(s: SampleOption) {
    setMessage(null);
    try {
      const res = await fetch(s.path);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      await handle(new File([blob], s.file_name, { type: s.mime }), true);
    } catch {
      setMessage({ kind: "error", text: `The sample file “${s.file_name}” could not be loaded.`, next: "Reload the page and try again, or upload your own file." });
    }
  }

  return (
    <div className="space-y-4">
      <div
        onDragOver={(e) => { e.preventDefault(); setOver(true); }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          const f = e.dataTransfer.files[0];
          if (f) void handle(f, false);
        }}
        className={cn("flex flex-col items-center gap-3 rounded-2xl border-2 border-dashed p-8 text-center transition-colors", over ? "border-brand bg-brand/10" : "border-white/15 bg-surface")}
      >
        <Icon className="size-8 text-brand-bright" aria-hidden />
        <p className="font-heading text-lg font-semibold">{rule.label}</p>
        <p className="max-w-md text-sm text-muted">{rule.helper}</p>
        <input
          ref={inputRef}
          id={inputId}
          type="file"
          accept={rule.accept}
          className="sr-only"
          onChange={(e) => {
            const f = e.target.files?.[0];
            if (f) void handle(f, false);
            e.target.value = "";
          }}
        />
        <Button type="button" variant="outline" onClick={() => inputRef.current?.click()} loading={busy}>
          <UploadCloud aria-hidden /> Choose file
        </Button>
        <p className="text-xs text-muted">or drag and drop it here</p>
      </div>

      <div>
        <p className="mb-2 font-mono text-xs uppercase tracking-wider text-muted">Or use a bundled sample (synthetic)</p>
        <div className="flex flex-wrap gap-2">
          {samples.map((s) => (
            <Button key={s.id} type="button" variant="ghost" size="sm" className="h-auto whitespace-normal border border-white/10 py-2 text-left normal-case tracking-normal" onClick={() => void loadSample(s)} disabled={busy}>
              {s.label}
            </Button>
          ))}
        </div>
      </div>

      {message && (
        <div role={message.kind === "error" ? "alert" : "status"} className={cn("rounded-xl border p-3 text-sm", message.kind === "error" ? "border-danger/50 bg-danger/10" : "border-caution/50 bg-caution/10")}>
          <p>{message.text}</p>
          {message.next && <p className="mt-1 text-muted"><span className="font-medium text-fg">What you can do: </span>{message.next}</p>}
        </div>
      )}
    </div>
  );
}
