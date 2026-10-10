"use client";

/**
 * Client-side app state: company, uploaded evidence, extraction results, reconciliation run and the
 * append-only review history. Persisted to localStorage (every access guarded) so a refresh keeps the demo.
 * Nothing is marked "processed" until the api adapter confirms it (no invented success states).
 */
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "./api-client";
import type {
  CompanyBundle,
  CompanyInput,
  CsvSummary,
  Finding,
  ImageResult,
  Invoice,
  ReconciliationResponse,
  ReviewAction,
  UploadKind,
  UploadedFile,
} from "./contracts";
import { ApiClientError, toApiClientError } from "./errors";
import { sha256Hex } from "./hash";
import { appendAction, clearHistory, effectiveState, loadHistory, saveHistory, type ReviewInput } from "./review-store";
import { validateFileMeta } from "./upload-validation";

const KEY = "eprlens.state.v1";

interface Persisted {
  company: CompanyBundle | null;
  uploads: UploadedFile[];
  image: { fileId: string; result: ImageResult } | null;
  invoice: Invoice | null;
  csv: CsvSummary | null;
  reconciliation: ReconciliationResponse | null;
}

const EMPTY: Persisted = { company: null, uploads: [], image: null, invoice: null, csv: null, reconciliation: null };

export interface AddFileOutcome {
  ok: boolean;
  message?: string;
  next_step?: string;
  duplicateOf?: UploadedFile;
}

interface Ctx extends Persisted {
  hydrated: boolean;
  history: ReviewAction[];
  busy: Record<string, boolean>;
  setCompany(c: CompanyBundle): void;
  createCompany(input: CompanyInput): Promise<CompanyBundle>;
  loadDemoCompany(): Promise<CompanyBundle>;
  addFile(kind: UploadKind, file: File, opts?: { sample?: boolean }): Promise<AddFileOutcome>;
  removeUpload(id: string): void;
  runReconciliation(): Promise<void>;
  reviewFinding(finding: Finding, input: ReviewInput): void;
  stateOf(finding: Finding): ReturnType<typeof effectiveState>;
  resetDemo(): void;
}

const AppCtx = createContext<Ctx | null>(null);

function safeStorage(): Storage | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<Persisted>(EMPTY);
  const [history, setHistory] = useState<ReviewAction[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const stateRef = useRef(state);
  // Single writer: keeps the ref in sync immediately so async flows (add file → reconcile) never read stale state.
  const update = useCallback((fn: (s: Persisted) => Persisted) => {
    const next = fn(stateRef.current);
    stateRef.current = next;
    setState(next);
  }, []);

  useEffect(() => {
    const st = safeStorage();
    try {
      const raw = st?.getItem(KEY);
      if (raw) update(() => ({ ...EMPTY, ...(JSON.parse(raw) as Partial<Persisted>) }));
    } catch {
      /* corrupted storage → start clean */
    }
    setHistory(loadHistory(st));
    setHydrated(true);
  }, [update]);

  useEffect(() => {
    if (!hydrated) return;
    try {
      const slim: Persisted = { ...state, csv: state.csv && state.csv.rows.length <= 200 ? state.csv : state.csv ? { ...state.csv, rows: [] } : null };
      safeStorage()?.setItem(KEY, JSON.stringify(slim));
    } catch {
      /* storage full or blocked: the app keeps working in memory */
    }
  }, [state, hydrated]);

  useEffect(() => {
    api.setActiveCompany(state.company?.company.company_id ?? null);
  }, [state.company]);

  const patch = useCallback((p: Partial<Persisted>) => update((s) => ({ ...s, ...p })), [update]);
  const setUploadStatus = useCallback(
    (id: string, status: UploadedFile["status"]) => update((s) => ({ ...s, uploads: s.uploads.map((u) => (u.id === id ? { ...u, status } : u)) })),
    [update],
  );
  const setBusyKey = (k: string, v: boolean) => setBusy((b) => ({ ...b, [k]: v }));

  const addFile = useCallback<Ctx["addFile"]>(
    async (kind, file, opts) => {
      const check = validateFileMeta(kind, file);
      if (!check.ok) return { ok: false, message: check.message, next_step: check.next_step };

      const sha256 = await sha256Hex(await file.arrayBuffer());
      const prior = stateRef.current.uploads.find((u) => u.sha256 === sha256 && u.kind === kind);
      const id = `${kind}-${sha256.slice(0, 8)}-${Date.now().toString(36)}`;
      const upload: UploadedFile = {
        id,
        kind,
        name: file.name,
        size_bytes: file.size,
        mime: file.type,
        sha256,
        uploaded_at: new Date().toISOString(),
        synthetic_sample: !!opts?.sample,
        status: prior ? "validated" : "processing",
        duplicate_of: prior?.id ?? null,
      };
      update((s) => ({ ...s, uploads: [...s.uploads, upload] }));
      if (prior) {
        // Warn and link; never silently discard and never re-run extraction on identical bytes.
        return { ok: true, duplicateOf: prior, message: `“${file.name}” has the same content as an earlier upload (${prior.name}).`, next_step: "Its earlier results are kept; remove the duplicate from the register if it was a mistake." };
      }

      setBusyKey(id, true);
      try {
        if (kind === "image") {
          const result = await api.classifyImage(file);
          patch({ image: { fileId: id, result } });
          setUploadStatus(id, result.uncertain ? "needs_review" : "extracted");
        } else if (kind === "invoice") {
          const invoice = await api.analyzeInvoice(file);
          patch({ invoice, reconciliation: null });
          setUploadStatus(id, invoice.extraction.status === "success" ? "extracted" : "needs_review");
        } else {
          const csv = await api.analyzeCsv(file);
          patch({ csv, reconciliation: null });
          setUploadStatus(id, csv.missing_required_columns.length ? "needs_review" : "extracted");
        }
        return { ok: true };
      } catch (e) {
        const err = toApiClientError(e);
        setUploadStatus(id, "failed");
        return { ok: false, message: err.message, next_step: err.next_step };
      } finally {
        setBusyKey(id, false);
      }
    },
    [patch, setUploadStatus, update],
  );

  const value = useMemo<Ctx>(
    () => ({
      ...state,
      hydrated,
      history,
      busy,
      setCompany: (company) => patch({ company }),
      async createCompany(input) {
        const company = await api.createCompany(input);
        update(() => ({ ...EMPTY, company }));
        setHistory([]);
        clearHistory(safeStorage());
        return company;
      },
      async loadDemoCompany() {
        const company = await api.getDemoCompany();
        update(() => ({ ...EMPTY, company }));
        setHistory([]);
        clearHistory(safeStorage());
        return company;
      },
      addFile,
      removeUpload: (id) =>
        update((s) => ({
          ...s,
          uploads: s.uploads.filter((u) => u.id !== id),
          image: s.image?.fileId === id ? null : s.image,
        })),
      async runReconciliation() {
        const { invoice, csv } = stateRef.current;
        if (!invoice || !csv) {
          throw new ApiClientError("missing_inputs", "Reconciliation needs both a transaction CSV and an invoice.", "Upload (or pick a sample) for the missing item on the Workspace page.");
        }
        setBusyKey("reconcile", true);
        try {
          patch({ reconciliation: await api.reconcile({ invoice, csv }) });
        } finally {
          setBusyKey("reconcile", false);
        }
      },
      reviewFinding(finding, input) {
        setHistory((h) => {
          const next = appendAction(h, finding, input, { actor: stateRef.current.company?.company.company_name ?? "demo reviewer", now: new Date() });
          saveHistory(safeStorage(), next);
          return next;
        });
      },
      stateOf: (finding) => effectiveState(finding, history),
      resetDemo() {
        update(() => EMPTY);
        setHistory([]);
        clearHistory(safeStorage());
        try {
          safeStorage()?.removeItem(KEY);
        } catch {
          /* ignore */
        }
      },
    }),
    [state, hydrated, history, busy, addFile, patch, update],
  );

  return <AppCtx.Provider value={value}>{children}</AppCtx.Provider>;
}

export function useApp(): Ctx {
  const ctx = useContext(AppCtx);
  if (!ctx) throw new Error("useApp must be used inside <AppProvider>");
  return ctx;
}
