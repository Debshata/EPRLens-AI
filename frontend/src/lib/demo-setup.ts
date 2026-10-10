import sampleFiles from "@/lib/mocks/sample-files.json";
import type { useApp } from "@/lib/app-state";

type App = ReturnType<typeof useApp>;

const MIME: Record<string, string> = { csv: "text/csv", invoice: "application/pdf", image: "image/png" };

async function sampleFile(id: string): Promise<File> {
  const s = sampleFiles.samples.find((x) => x.id === id);
  if (!s) throw new Error(`Unknown sample ${id}`);
  const res = await fetch(s.path);
  if (!res.ok) throw new Error(`Sample ${s.file_name} could not be loaded (HTTP ${res.status}).`);
  return new File([await res.blob()], s.file_name, { type: MIME[s.kind] });
}

/** One-click demo: demo company → sample CSV + invoice + photo → reconcile. Every step uses the normal pipeline. */
export async function runFullDemo(app: Pick<App, "loadDemoCompany" | "addFile" | "runReconciliation">): Promise<void> {
  await app.loadDemoCompany();
  const csv = await app.addFile("csv", await sampleFile("csv-demo"), { sample: true });
  const inv = await app.addFile("invoice", await sampleFile("invoice-mismatch"), { sample: true });
  const img = await app.addFile("image", await sampleFile("image-bottle"), { sample: true });
  const failed = [csv, inv, img].find((r) => !r.ok);
  if (failed) throw new Error(`${failed.message ?? "A sample could not be processed."} ${failed.next_step ?? ""}`);
  await app.runReconciliation();
}
