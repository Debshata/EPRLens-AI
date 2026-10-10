/**
 * Typed data contracts shared by the mock adapter, the live adapter and every component.
 * Every fixture in src/lib/mocks and every /api/* response is parsed with these schemas, so mock
 * mode and live mode cannot silently drift apart. Extra fields from the backend are tolerated
 * (looseObject); missing or mistyped required fields fail loudly.
 *
 * Quantities are always kg internally. Original value + unit are kept next to the normalised value.
 * Nothing here is a legal determination (see `legal_determination: false`).
 */
import { z } from "zod";

// ---------- shared ----------
export const Severity = z.enum(["low", "medium", "high"]);
export type Severity = z.infer<typeof Severity>;

/** Lifecycle of a finding in the review workflow (UX spec: original value is never overwritten). */
export const ReviewState = z.enum(["open", "needs_review", "accepted", "rejected"]);
export type ReviewState = z.infer<typeof ReviewState>;

/** How well supported a displayed quantity is — drives the badge variants. */
export const EvidenceStatus = z.enum([
  "document_supported",
  "declared",
  "estimated",
  "needs_review",
  "unknown",
  "reviewed",
]);
export type EvidenceStatus = z.infer<typeof EvidenceStatus>;

export const FixtureMeta = z.looseObject({
  synthetic: z.literal(true),
  watermark: z.string(),
  seed: z.number().optional(),
  generator_version: z.string().optional(),
  dataset_sha256: z.string().optional(),
  note: z.string(),
});
export type FixtureMeta = z.infer<typeof FixtureMeta>;

// ---------- company ----------
export const CompanyProfile = z.looseObject({
  company_id: z.string(),
  company_name: z.string(),
  industry: z.string(),
  company_size: z.string().optional(),
  turnover_cr: z.number().nullable(),
  manufacturer: z.boolean(),
  importer: z.boolean(),
  brand_owner: z.boolean(),
  states_operated: z.array(z.string()),
  headquarters_state: z.string().optional(),
  epr_registered: z.boolean().nullable().optional(),
  registration_status: z.string().optional(),
  business_description: z.string().optional(),
  annual_units: z.number().nullable().optional(),
  synthetic_flag: z.boolean().optional(),
});
export type CompanyProfile = z.infer<typeof CompanyProfile>;

export const CompanyBundle = z.looseObject({
  _meta: FixtureMeta,
  company: CompanyProfile,
  roles: z.looseObject({
    producer: z.boolean(),
    importer: z.boolean(),
    brand_owner: z.boolean(),
    manufacturer: z.boolean(),
  }),
  rules_version: z.string(),
});
export type CompanyBundle = z.infer<typeof CompanyBundle>;

/** Input of the onboarding form (also what POST /company would receive). */
export const CompanyInput = z.object({
  company_name: z.string().trim().min(2, "Enter the registered business name."),
  roles: z.array(z.enum(["producer", "importer", "brand_owner", "manufacturer"])).min(1, "Pick at least one role, or choose Unknown."),
  roles_unknown: z.boolean().default(false),
  industry: z.string().min(1, "Choose an industry."),
  turnover_cr: z.number().nonnegative("Turnover cannot be negative.").nullable(),
  turnover_unknown: z.boolean().default(false),
  states_operated: z.array(z.string()).default([]),
  packaging_types: z.array(z.string()).default([]),
  registration_status: z.enum(["registered", "not_registered", "in_progress", "unknown"]).default("unknown"),
  business_description: z.string().max(600).default(""),
});
export type CompanyInput = z.input<typeof CompanyInput>;

export const ApplicabilityOutcome = z.object({
  status: z.enum(["potentially_applicable", "needs_more_information", "not_indicated"]),
  statement: z.string(),
  reasons: z.array(z.string()),
  missing: z.array(z.string()),
  rules_version: z.string(),
  legal_determination: z.literal(false),
});
export type ApplicabilityOutcome = z.infer<typeof ApplicabilityOutcome>;

// ---------- image classification (WP1 output shape, exactly) ----------
export const MaterialClass = z.enum(["plastic", "paper", "cardboard", "metal", "glass", "battery", "trash_other"]);
export type MaterialClass = z.infer<typeof MaterialClass>;

export const ImageResult = z.object({
  predicted_class: MaterialClass,
  confidence: z.number().min(0).max(1),
  uncertain: z.boolean(),
  model_version: z.string(),
});
export type ImageResult = z.infer<typeof ImageResult>;

export const ImageResultFixture = z.looseObject({
  _meta: FixtureMeta,
  results: z.record(z.string(), ImageResult),
  classes: z.array(MaterialClass),
});

// ---------- invoice extraction ----------
export const EvidenceField = z.object({
  field: z.string(),
  raw_text: z.string(),
  normalized_value: z.union([z.string(), z.number()]),
  unit: z.string().nullable(),
  source_ref: z.string(),
  confidence_proxy: z.number().min(0).max(1),
  review_state: z.enum(["unreviewed", "needs_review", "accepted", "rejected"]),
  status: EvidenceStatus,
});
export type EvidenceField = z.infer<typeof EvidenceField>;

export const InvoiceLine = z.looseObject({
  line_reference: z.string(),
  transaction_id: z.string().nullable().optional(),
  product_id: z.string().nullable().optional(),
  component_id: z.string().nullable().optional(),
  page: z.number(),
  line_no: z.number(),
  description: z.string(),
  material: z.string().nullable(),
  /** null = the document gives no quantity (never shown as zero). */
  quantity: z.number().nullable(),
  unit: z.string(),
  printed_quantity: z.string().optional(),
  printed_unit: z.string().optional(),
  normalized_quantity_kg: z.number().nullable(),
  conversion_rule: z.string().optional(),
  amount: z.number().nullable(),
});
export type InvoiceLine = z.infer<typeof InvoiceLine>;

export const Invoice = z.looseObject({
  document_id: z.string(),
  invoice_id: z.string().optional(),
  invoice_number: z.string(),
  invoice_type: z.string().optional(),
  invoice_date: z.string(),
  vendor: z.looseObject({ name: z.string(), gstin: z.string().nullable().optional() }),
  buyer: z.looseObject({ name: z.string(), gstin: z.string().nullable().optional() }).optional(),
  currency: z.string(),
  total_amount: z.number().nullable(),
  page_count: z.number(),
  lines: z.array(InvoiceLine),
  fields: z.array(EvidenceField),
  source: z.looseObject({ file_name: z.string(), sha256: z.string(), synthetic: z.boolean() }),
  extraction: z.looseObject({
    method: z.string(),
    status: z.enum(["success", "needs_review", "failed"]),
    parser_version: z.string(),
  }),
});
export type Invoice = z.infer<typeof Invoice>;

export const InvoiceFixture = z.looseObject({ _meta: FixtureMeta, invoice: Invoice });

// ---------- reconciliation findings ----------
export const QuantityRef = z.looseObject({
  label: z.string(),
  raw_value: z.union([z.string(), z.number()]),
  raw_unit: z.string().nullable(),
  value_kg: z.number().nullable(),
  source_ref: z.string(),
});
export type QuantityRef = z.infer<typeof QuantityRef>;

export const Finding = z.looseObject({
  finding_id: z.string(),
  type: z.string(),
  anomaly_code: z.string().optional(),
  title: z.string(),
  severity: Severity,
  review_state: ReviewState,
  company_id: z.string(),
  invoice_id: z.string().nullable(),
  invoice_number: z.string().nullable(),
  document_id: z.string().nullable(),
  counterparty: z.string().nullable(),
  material: z.string().nullable(),
  component: z.string().nullable(),
  /** Reference side (e.g. the document). */
  expected: QuantityRef,
  /** Compared side (e.g. the internal record). */
  observed: QuantityRef,
  difference_kg: z.number().nullable(),
  rule_ids: z.array(z.string()),
  rule_version: z.string(),
  detected_by: z.array(z.enum(["rule", "ml_outlier"])),
  /** Isolation-forest style score; NOT a probability of non-compliance. null = not computed. */
  model_score: z.number().nullable(),
  model_threshold: z.number().optional(),
  model_version: z.string().optional(),
  explanation: z.string(),
  legal_determination: z.literal(false),
});
export type Finding = z.infer<typeof Finding>;

export const ReconciliationResponse = z.looseObject({
  _meta: FixtureMeta.optional(),
  analysis_id: z.string(),
  schema_version: z.string(),
  company_id: z.string(),
  rules_version: z.string(),
  tolerances: z.object({ qty_tolerance_kg: z.number(), qty_tolerance_rel: z.number() }),
  findings: z.array(Finding),
});
export type ReconciliationResponse = z.infer<typeof ReconciliationResponse>;

// ---------- anomaly (detect-anomaly Lambda) ----------
export const AnomalyResult = z.looseObject({
  record_id: z.string(),
  is_anomaly: z.boolean(),
  anomaly_score: z.number(),
  threshold: z.number(),
  ml_flag: z.boolean(),
  rule_findings: z.array(z.object({ rule_id: z.string(), severity: Severity, reason: z.string() })),
  model_version: z.string(),
  status: z.string(),
});
export type AnomalyResult = z.infer<typeof AnomalyResult>;

export const AnomalyFixture = z.looseObject({
  _meta: FixtureMeta,
  results: z.array(AnomalyResult),
  decision_rule: z.string(),
});

// ---------- forecast ----------
export const ForecastHistoryPoint = z.object({
  month: z.string().regex(/^\d{4}-\d{2}$/),
  packaging_kg: z.number(),
  kind: z.literal("observed"),
});
export const ForecastFuturePoint = z.object({
  month: z.string().regex(/^\d{4}-\d{2}$/),
  packaging_kg: z.number(),
  /** `model` = direct forecast-v1 output. `projected` = recursive, model output fed back as history. */
  kind: z.enum(["model", "projected"]),
  per_product: z.record(z.string(), z.number()).optional(),
});
export type ForecastFuturePoint = z.infer<typeof ForecastFuturePoint>;

export const ForecastResponse = z.looseObject({
  _meta: FixtureMeta.optional(),
  company_id: z.string(),
  basis: z.string(),
  history: z.array(ForecastHistoryPoint),
  forecast: z.looseObject({
    model_version: z.string(),
    model_name: z.string(),
    target: z.string(),
    interval: z.null(),
    interval_note: z.string(),
    synthetic_only: z.boolean(),
    warning: z.string(),
    baseline: z.object({ name: z.string(), next_month_kg: z.number() }),
    metrics_test: z.looseObject({
      mae_kg: z.number(),
      rmse_kg: z.number(),
      r2: z.number(),
      baseline_last_value_mae_kg: z.number(),
      source: z.string(),
    }),
    points: z.array(ForecastFuturePoint).min(1),
  }),
});
export type ForecastResponse = z.infer<typeof ForecastResponse>;

// ---------- scenario / simulator ----------
export const ScenarioRequest = z.object({
  product_id: z.string(),
  component_id: z.string(),
  units: z.number().nonnegative(),
  baseline_g_per_unit: z.number().positive(),
  proposed_g_per_unit: z.number().positive(),
});
export type ScenarioRequest = z.infer<typeof ScenarioRequest>;

export const ScenarioResult = z.object({
  baseline_kg: z.number(),
  proposed_kg: z.number(),
  reduction_kg: z.number(),
  reduction_pct: z.number(),
  formula: z.string(),
  hypothetical: z.literal(true),
  disclaimer: z.string(),
});
export type ScenarioResult = z.infer<typeof ScenarioResult>;

export const SimulatorComponent = z.looseObject({
  component_id: z.string(),
  component_name: z.string(),
  material: z.string(),
  weight_per_unit_g: z.number(),
  plastic_epr_relevant: z.boolean().optional(),
  weight_status: z.enum(["declared", "estimated", "unknown"]),
});
export const SimulatorProduct = z.looseObject({
  product_id: z.string(),
  product_name: z.string(),
  units_fy2025_26: z.number(),
  components: z.array(SimulatorComponent),
});
export const SimulatorFixture = z.looseObject({
  _meta: FixtureMeta,
  company_id: z.string(),
  period: z.string(),
  default: z.object({ product_id: z.string(), component_id: z.string(), proposed_weight_g: z.number() }),
  products: z.array(SimulatorProduct),
});
export type SimulatorFixture = z.infer<typeof SimulatorFixture>;

/** Example what-if scenarios shipped with the synthetic dataset (5 / 15 / 25 % lighter PET bottle). */
export const ScenarioPresetFixture = z.looseObject({
  _meta: FixtureMeta,
  scenarios: z.array(
    z.looseObject({
      scenario_id: z.string(),
      product_id: z.string(),
      component_id: z.string(),
      reduction_pct: z.number(),
      baseline_weight_g: z.number(),
      proposed_weight_g: z.number(),
      units: z.number(),
    }),
  ),
});
export type ScenarioPresetFixture = z.infer<typeof ScenarioPresetFixture>;

// ---------- dashboard ----------
export const DashboardSummary = z.looseObject({
  _meta: FixtureMeta,
  company_id: z.string(),
  monthly_placed_on_market: z.array(
    z.object({ month: z.string(), plastic_kg: z.number(), total_packaging_kg: z.number() }),
  ),
  material_mix_fy2025_26_kg: z.record(z.string(), z.number()),
  recycling_by_fy: z.record(
    z.string(),
    z.object({
      waste_generated_kg: z.number(),
      waste_collected_kg: z.number(),
      waste_recycled_kg: z.number(),
      credits_documented_kg: z.number(),
    }),
  ),
  anomaly_label_counts: z.record(z.string(), z.number()),
});
export type DashboardSummary = z.infer<typeof DashboardSummary>;

// ---------- uploads ----------
export const UploadKind = z.enum(["csv", "invoice", "image"]);
export type UploadKind = z.infer<typeof UploadKind>;

export const UploadedFile = z.object({
  id: z.string(),
  kind: UploadKind,
  name: z.string(),
  size_bytes: z.number(),
  mime: z.string(),
  sha256: z.string(),
  uploaded_at: z.string(),
  synthetic_sample: z.boolean(),
  status: z.enum(["validated", "processing", "extracted", "needs_review", "failed"]),
  duplicate_of: z.string().nullable(),
});
export type UploadedFile = z.infer<typeof UploadedFile>;

export const CsvSummary = z.object({
  file_name: z.string(),
  row_count: z.number(),
  columns: z.array(z.string()),
  missing_required_columns: z.array(z.string()),
  rows: z.array(z.record(z.string(), z.string())),
});
export type CsvSummary = z.infer<typeof CsvSummary>;

// ---------- review actions (append-only history) ----------
export const ReviewAction = z.object({
  action_id: z.string(),
  finding_id: z.string(),
  kind: z.enum(["accept_correction", "reject_suggestion", "mark_needs_review", "reopen"]),
  actor: z.string(),
  timestamp: z.string(),
  /** Always the untouched original value (kg) of the observed side at the time of action. */
  original_value_kg: z.number().nullable(),
  /** Reviewer-proposed value (kg); only for accept_correction. */
  proposed_value_kg: z.number().nullable(),
  reason: z.string(),
});
export type ReviewAction = z.infer<typeof ReviewAction>;

/** Standard error envelope returned by every /api/* handler. Always says what the user can do next. */
export const ApiError = z.object({
  code: z.string(),
  message: z.string(),
  next_step: z.string(),
});
export type ApiError = z.infer<typeof ApiError>;
