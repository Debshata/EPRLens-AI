"use client";

import { ArrowRight, CheckCircle2, Table2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { ErrorState } from "@/components/data/data-state";
import { Disclaimer } from "@/components/data/disclaimer";
import { PageHeader } from "@/components/data/page-header";
import { InvoiceExtractionTable } from "@/components/upload/invoice-extraction-table";
import { MaterialPredictionCard } from "@/components/upload/material-prediction-card";
import { SourceRegister } from "@/components/upload/source-register";
import { UploadDropzone, type SampleOption } from "@/components/upload/upload-dropzone";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useApp } from "@/lib/app-state";
import type { UploadKind } from "@/lib/contracts";
import sampleFiles from "@/lib/mocks/sample-files.json";

const MIME: Record<string, string> = { csv: "text/csv", invoice: "application/pdf", image: "image/png" };

function samplesFor(kind: UploadKind): SampleOption[] {
  return sampleFiles.samples.filter((s) => s.kind === kind).map((s) => ({ id: s.id, label: s.description, path: s.path, file_name: s.file_name, mime: MIME[kind] }));
}

export default function WorkspacePage() {
  const router = useRouter();
  const app = useApp();
  const [tab, setTab] = useState<UploadKind>("csv");
  const [reconcileError, setReconcileError] = useState<unknown>(null);
  const [imageUrl, setImageUrl] = useState<string | null>(null);

  const imageUpload = app.image ? app.uploads.find((u) => u.id === app.image!.fileId) : undefined;
  const imageName = imageUpload?.name;

  // Preview for bundled samples (user files are not persisted, so only samples can be re-previewed after refresh).
  useEffect(() => {
    const s = sampleFiles.samples.find((x) => x.file_name === imageName);
    setImageUrl(s ? s.path : null);
  }, [imageName]);

  const ready = !!app.csv && !!app.invoice;
  const csvOk = app.csv && app.csv.missing_required_columns.length === 0;
  const sampleOpts = useMemo(() => ({ csv: samplesFor("csv"), invoice: samplesFor("invoice"), image: samplesFor("image") }), []);

  async function run() {
    setReconcileError(null);
    try {
      await app.runReconciliation();
      router.push("/app/review");
    } catch (e) {
      setReconcileError(e);
    }
  }

  const busyKind = (k: UploadKind) => app.uploads.some((u) => u.kind === k && app.busy[u.id]);

  return (
    <>
      <PageHeader
        kicker="Evidence"
        title="Upload evidence"
        description="Add the transaction CSV, a digital invoice PDF and a packaging photo. Each result shows where it came from and what is still unconfirmed."
      />

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,1fr)]">
        <div className="space-y-6">
          <Tabs value={tab} onValueChange={(v) => setTab(v as UploadKind)}>
            <TabsList aria-label="Evidence type">
              <TabsTrigger value="csv">Transaction CSV</TabsTrigger>
              <TabsTrigger value="invoice">Invoice PDF</TabsTrigger>
              <TabsTrigger value="image">Packaging photo</TabsTrigger>
            </TabsList>
            {(["csv", "invoice", "image"] as const).map((k) => (
              <TabsContent key={k} value={k} className="mt-4">
                <UploadDropzone kind={k} samples={sampleOpts[k]} busy={busyKind(k)} onFile={(f, o) => app.addFile(k, f, o)} />
              </TabsContent>
            ))}
          </Tabs>
          <SourceRegister uploads={app.uploads} onRemove={app.removeUpload} />
        </div>

        <div className="space-y-6">
          {app.image && <MaterialPredictionCard result={app.image.result} previewSrc={imageUrl} fileName={imageName} />}

          {app.csv && (
            <Card variant="standard" className="space-y-3" data-testid="csv-preview">
              <div className="flex items-center gap-2"><Table2 className="size-4 text-brand-bright" aria-hidden /><CardTitle>CSV preview</CardTitle></div>
              <CardDescription>
                <span className="num">{app.csv.file_name}</span> · <span className="num">{app.csv.row_count}</span> rows
              </CardDescription>
              {app.csv.missing_required_columns.length > 0 ? (
                <p role="alert" className="rounded-xl border border-danger/50 bg-danger/10 p-3 text-sm">
                  Missing required columns: <span className="num">{app.csv.missing_required_columns.join(", ")}</span>.
                  <span className="mt-1 block text-muted"><span className="font-medium text-fg">What you can do: </span>add these columns to the file and upload it again.</span>
                </p>
              ) : (
                <p className="flex items-center gap-2 text-sm text-brand-bright"><CheckCircle2 className="size-4" aria-hidden /> All required columns present.</p>
              )}
              {app.csv.rows.length > 0 && (
                <Table aria-label="First rows of the CSV">
                  <THead><TR className="hover:bg-transparent"><TH>Transaction</TH><TH>Date</TH><TH className="text-right">Quantity</TH><TH>Unit</TH></TR></THead>
                  <TBody>
                    {app.csv.rows.slice(0, 5).map((r) => (
                      <TR key={r.transaction_id}>
                        <TD className="num text-xs">{r.transaction_id}</TD><TD className="num text-xs">{r.date}</TD>
                        <TD className="num text-right">{r.raw_quantity}</TD><TD>{r.raw_unit}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </Card>
          )}

          {app.invoice && <InvoiceExtractionTable invoice={app.invoice} />}

          <Card variant="glass" className="space-y-4">
            <CardTitle>Reconcile</CardTitle>
            <CardDescription>Compare each invoice line with its linked record in the CSV. Quantities are converted to kg; the original value and unit are always kept.</CardDescription>
            {!ready && <p className="text-sm text-muted">Needs {!app.csv && "a transaction CSV"}{!app.csv && !app.invoice && " and "}{!app.invoice && "an invoice PDF"} first.</p>}
            {reconcileError != null && <ErrorState error={reconcileError} title="Reconciliation could not run" />}
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => void run()} disabled={!ready || !csvOk} loading={!!app.busy.reconcile}>
                Run reconciliation <ArrowRight aria-hidden />
              </Button>
              {app.reconciliation && (
                <Button asChild variant="outline"><Link href="/app/review">Open findings</Link></Button>
              )}
            </div>
          </Card>
          <Disclaimer />
        </div>
      </div>
    </>
  );
}
