"use client";

import { ArrowLeft, ArrowRight, Check, FlaskConical } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useId, useMemo, useState } from "react";
import { Disclaimer } from "@/components/data/disclaimer";
import { ErrorState } from "@/components/data/data-state";
import { SyntheticDataBadge } from "@/components/data/synthetic-data-badge";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { FieldError, Input, Label, Select, Textarea } from "@/components/ui/input";
import { assessApplicability } from "@/lib/applicability";
import { useApp } from "@/lib/app-state";
import { api } from "@/lib/api-client";
import type { CompanyInput } from "@/lib/contracts";
import { INDIAN_STATES, INDUSTRIES, PACKAGING_TYPES, REGISTRATION_OPTIONS, ROLE_OPTIONS } from "@/lib/options";
import { cn } from "@/lib/utils";

type Role = "producer" | "importer" | "brand_owner" | "manufacturer";

interface FormState {
  company_name: string;
  roles: Role[];
  roles_unknown: boolean;
  industry: string;
  turnover: string;
  turnover_unknown: boolean;
  states_operated: string[];
  registration_status: "registered" | "not_registered" | "in_progress" | "unknown";
  business_description: string;
  packaging_types: string[];
}

const EMPTY: FormState = {
  company_name: "", roles: [], roles_unknown: false, industry: "", turnover: "", turnover_unknown: false,
  states_operated: [], registration_status: "unknown", business_description: "", packaging_types: [],
};

const STEPS = ["Business", "Activities", "Materials", "Review"] as const;

function toInput(f: FormState): CompanyInput {
  return {
    company_name: f.company_name.trim(),
    roles: f.roles,
    roles_unknown: f.roles_unknown,
    industry: f.industry,
    turnover_cr: f.turnover_unknown || f.turnover.trim() === "" ? null : Number(f.turnover),
    turnover_unknown: f.turnover_unknown,
    states_operated: f.states_operated,
    packaging_types: f.packaging_types,
    registration_status: f.registration_status,
    business_description: f.business_description,
  };
}

type Errors = Partial<Record<"company_name" | "roles" | "industry" | "turnover", string>>;

function validateStep0(f: FormState): Errors {
  const e: Errors = {};
  if (f.company_name.trim().length < 2) e.company_name = "Enter the registered business name (at least 2 characters).";
  if (!f.roles.length && !f.roles_unknown) e.roles = "Choose at least one role, or tick “I don’t know yet”.";
  if (!f.industry) e.industry = "Choose the closest industry.";
  if (!f.turnover_unknown) {
    if (f.turnover.trim() === "") e.turnover = "Enter annual turnover in ₹ crore, or tick “Unknown”.";
    else if (!Number.isFinite(Number(f.turnover)) || Number(f.turnover) < 0) e.turnover = "Turnover must be a number of zero or more (₹ crore).";
  }
  return e;
}

function Chip({ pressed, onClick, children }: { pressed: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      aria-pressed={pressed}
      onClick={onClick}
      className={cn(
        "inline-flex min-h-11 items-center gap-1.5 rounded-full border px-4 text-sm transition-colors",
        pressed ? "border-brand bg-brand/15 text-brand-bright" : "border-white/15 text-muted hover:border-white/40 hover:text-fg",
      )}
    >
      {pressed && <Check className="size-3.5" aria-hidden />}
      {children}
    </button>
  );
}

function toggle<T>(list: T[], v: T): T[] {
  return list.includes(v) ? list.filter((x) => x !== v) : [...list, v];
}

function Inner() {
  const router = useRouter();
  const params = useSearchParams();
  const { createCompany, loadDemoCompany } = useApp();
  const uid = useId();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [errors, setErrors] = useState<Errors>({});
  const [demoValues, setDemoValues] = useState<FormState | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(null);

  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setForm((f) => ({ ...f, [k]: v }));

  async function fillDemo() {
    const demo = await api.getDemoCompany();
    const c = demo.company;
    const values: FormState = {
      company_name: c.company_name,
      roles: (["manufacturer", "brand_owner"] as Role[]).filter((r) => (r === "manufacturer" ? c.manufacturer : c.brand_owner)),
      roles_unknown: false,
      industry: c.industry,
      turnover: String(c.turnover_cr ?? ""),
      turnover_unknown: false,
      states_operated: c.states_operated,
      registration_status: c.epr_registered ? "registered" : "unknown",
      business_description: c.business_description ?? "",
      packaging_types: ["PET bottles", "HDPE / PP caps and closures", "Paper labels", "Corrugated cartons", "Glass bottles"],
    };
    setForm(values);
    setDemoValues(values);
    setErrors({});
  }

  useEffect(() => {
    if (params.get("demo") === "1") void fillDemo();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const input = useMemo(() => toInput(form), [form]);
  const applicability = useMemo(() => assessApplicability(input), [input]);
  const untouchedDemo = demoValues !== null && JSON.stringify(demoValues) === JSON.stringify(form);

  function next() {
    if (step === 0) {
      const e = validateStep0(form);
      setErrors(e);
      if (Object.keys(e).length) return;
    }
    setStep((s) => Math.min(s + 1, STEPS.length - 1));
  }

  async function create() {
    setSubmitting(true);
    setSubmitError(null);
    try {
      if (untouchedDemo) await loadDemoCompany();
      else await createCompany(input);
      router.push("/app/workspace");
    } catch (e) {
      setSubmitError(e);
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-10 md:py-14">
      <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-mono text-xs uppercase tracking-widest text-brand-bright">Company setup</p>
          <h1 className="font-heading text-3xl font-bold tracking-tight md:text-4xl">Tell us about the business</h1>
        </div>
        <Button variant="outline" size="sm" onClick={() => void fillDemo()}>
          <FlaskConical aria-hidden /> Use demo company
        </Button>
      </div>

      {untouchedDemo && (
        <p role="status" className="mb-6 flex flex-wrap items-center gap-2 rounded-xl border border-brand/40 bg-brand/10 p-3 text-sm text-brand-bright">
          <SyntheticDataBadge /> This is a wholly fictitious company (EcoFizz Beverages Pvt Ltd). Nothing here is a real business or record.
        </p>
      )}

      <ol className="mb-8 grid grid-cols-4 gap-2" aria-label="Progress">
        {STEPS.map((s, i) => (
          <li key={s} aria-current={i === step ? "step" : undefined} className={cn("rounded-xl border px-3 py-2 text-center text-xs font-medium sm:text-sm", i === step ? "border-brand bg-brand/10 text-brand-bright" : i < step ? "border-white/20 text-fg" : "border-white/10 text-muted")}>
            <span className="num mr-1 text-muted">{i + 1}</span>
            <span className="hidden sm:inline">{s}</span>
            <span className="sm:hidden">{s.slice(0, 4)}</span>
          </li>
        ))}
      </ol>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <Card>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (step < STEPS.length - 1) next();
            }}
            noValidate
            className="space-y-6"
          >
            {step === 0 && (
              <>
                <CardTitle>Business</CardTitle>
                <div>
                  <Label htmlFor={`${uid}-name`}>Business name</Label>
                  <Input id={`${uid}-name`} value={form.company_name} onChange={(e) => set("company_name", e.target.value)} aria-invalid={!!errors.company_name} aria-describedby={errors.company_name ? `${uid}-name-err` : undefined} placeholder="e.g. Example Beverages Pvt Ltd" autoComplete="organization" />
                  <FieldError id={`${uid}-name-err`}>{errors.company_name}</FieldError>
                </div>
                <fieldset aria-describedby={errors.roles ? `${uid}-roles-err` : undefined}>
                  <legend className="mb-1.5 font-mono text-xs uppercase tracking-wider text-muted">Role(s)</legend>
                  <div className="flex flex-wrap gap-2">
                    {ROLE_OPTIONS.map((r) => (
                      <Chip key={r.id} pressed={form.roles.includes(r.id)} onClick={() => setForm((f) => ({ ...f, roles: toggle(f.roles, r.id), roles_unknown: false }))}>
                        {r.label}
                      </Chip>
                    ))}
                    <Chip pressed={form.roles_unknown} onClick={() => setForm((f) => ({ ...f, roles_unknown: !f.roles_unknown, roles: [] }))}>I don’t know yet</Chip>
                  </div>
                  <FieldError id={`${uid}-roles-err`}>{errors.roles}</FieldError>
                </fieldset>
                <div className="grid gap-5 sm:grid-cols-2">
                  <div>
                    <Label htmlFor={`${uid}-industry`}>Industry</Label>
                    <Select id={`${uid}-industry`} value={form.industry} onChange={(e) => set("industry", e.target.value)} aria-invalid={!!errors.industry} aria-describedby={errors.industry ? `${uid}-ind-err` : undefined}>
                      <option value="">Select…</option>
                      {INDUSTRIES.map((i) => <option key={i} value={i}>{i}</option>)}
                    </Select>
                    <FieldError id={`${uid}-ind-err`}>{errors.industry}</FieldError>
                  </div>
                  <div>
                    <Label htmlFor={`${uid}-turnover`}>Annual turnover (₹ crore)</Label>
                    <Input id={`${uid}-turnover`} inputMode="decimal" type="number" min={0} step="any" disabled={form.turnover_unknown} value={form.turnover} onChange={(e) => set("turnover", e.target.value)} aria-invalid={!!errors.turnover} aria-describedby={errors.turnover ? `${uid}-to-err` : undefined} placeholder="e.g. 180" />
                    <label className="mt-2 flex min-h-11 items-center gap-2 text-sm text-muted">
                      <input type="checkbox" className="size-4 accent-[var(--green-primary)]" checked={form.turnover_unknown} onChange={(e) => setForm((f) => ({ ...f, turnover_unknown: e.target.checked, turnover: e.target.checked ? "" : f.turnover }))} />
                      Unknown
                    </label>
                    <FieldError id={`${uid}-to-err`}>{errors.turnover}</FieldError>
                  </div>
                </div>
              </>
            )}

            {step === 1 && (
              <>
                <CardTitle>Activities</CardTitle>
                <fieldset>
                  <legend className="mb-1.5 font-mono text-xs uppercase tracking-wider text-muted">Operating states (optional)</legend>
                  <div className="flex flex-wrap gap-2">
                    {INDIAN_STATES.map((s) => (
                      <Chip key={s} pressed={form.states_operated.includes(s)} onClick={() => set("states_operated", toggle(form.states_operated, s))}>{s}</Chip>
                    ))}
                  </div>
                </fieldset>
                <div>
                  <Label htmlFor={`${uid}-reg`}>EPR registration status</Label>
                  <Select id={`${uid}-reg`} value={form.registration_status} onChange={(e) => set("registration_status", e.target.value as FormState["registration_status"])}>
                    {REGISTRATION_OPTIONS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
                  </Select>
                  <p className="mt-1.5 text-xs text-muted">Unknown is fine — it will show as a gap, not as non-compliance.</p>
                </div>
                <div>
                  <Label htmlFor={`${uid}-desc`}>Short business description (optional)</Label>
                  <Textarea id={`${uid}-desc`} maxLength={600} value={form.business_description} onChange={(e) => set("business_description", e.target.value)} placeholder="What do you sell, in which packaging, and where?" />
                  <p className="num mt-1 text-right text-xs text-muted">{form.business_description.length}/600</p>
                </div>
              </>
            )}

            {step === 2 && (
              <>
                <CardTitle>Packaging used</CardTitle>
                <CardDescription>Select every type you use. This only sets expectations — quantities come from your uploaded evidence.</CardDescription>
                <div className="flex flex-wrap gap-2">
                  {PACKAGING_TYPES.map((p) => (
                    <Chip key={p} pressed={form.packaging_types.includes(p)} onClick={() => set("packaging_types", toggle(form.packaging_types, p))}>{p}</Chip>
                  ))}
                </div>
              </>
            )}

            {step === 3 && (
              <>
                <CardTitle>Review</CardTitle>
                <dl className="grid gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
                  {[
                    ["Business", form.company_name || "—"],
                    ["Role(s)", form.roles_unknown ? "Unknown" : form.roles.map((r) => ROLE_OPTIONS.find((o) => o.id === r)?.label).join(", ") || "—"],
                    ["Industry", form.industry || "—"],
                    ["Turnover", form.turnover_unknown ? "Unknown" : form.turnover ? `₹${form.turnover} crore` : "—"],
                    ["Operating states", form.states_operated.join(", ") || "Not given"],
                    ["Registration", REGISTRATION_OPTIONS.find((o) => o.id === form.registration_status)?.label ?? "Unknown"],
                    ["Packaging", form.packaging_types.join(", ") || "Not given"],
                  ].map(([k, v]) => (
                    <div key={k}>
                      <dt className="font-mono text-[11px] uppercase tracking-wider text-muted">{k}</dt>
                      <dd className="mt-0.5">{v}</dd>
                    </div>
                  ))}
                </dl>
                {applicability.missing.length > 0 && (
                  <div className="rounded-xl border border-caution/40 bg-caution/5 p-4 text-sm">
                    <p className="mb-1 font-medium text-caution">Missing or incomplete</p>
                    <ul className="list-disc space-y-1 pl-5 text-fg/90">{applicability.missing.map((m) => <li key={m}>{m}</li>)}</ul>
                  </div>
                )}
                {submitError != null && <ErrorState error={submitError} title="Could not create the workspace" />}
              </>
            )}

            <div className="flex items-center justify-between gap-3 border-t border-white/10 pt-5">
              <Button type="button" variant="ghost" onClick={() => setStep((s) => Math.max(0, s - 1))} disabled={step === 0}>
                <ArrowLeft aria-hidden /> Back
              </Button>
              {step < STEPS.length - 1 ? (
                <Button type="submit">Continue <ArrowRight aria-hidden /></Button>
              ) : (
                <Button type="button" onClick={() => void create()} loading={submitting}>Create workspace <ArrowRight aria-hidden /></Button>
              )}
            </div>
          </form>
        </Card>

        <aside className="space-y-4">
          <Card variant="glass">
            <CardTitle className="text-base">Potential applicability</CardTitle>
            <p className="mt-2 text-sm text-fg/90" data-testid="applicability-statement">{applicability.statement}</p>
            {applicability.reasons.length > 0 && (
              <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-muted">{applicability.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
            )}
            <div className="mt-3 flex flex-wrap gap-2">
              <Badge variant="needs_review">Requires verification</Badge>
              <Badge variant="neutral">{applicability.rules_version}</Badge>
            </div>
          </Card>
          <Disclaimer>Applicability hints come from versioned demo rules based on a secondary handbook. They are not a legal determination — verify with official CPCB sources.</Disclaimer>
        </aside>
      </div>
    </div>
  );
}

export function CompanyForm() {
  return (
    <Suspense fallback={<div className="p-10 text-muted">Loading…</div>}>
      <Inner />
    </Suspense>
  );
}
