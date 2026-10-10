import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ErrorState } from "@/components/data/data-state";
import { SyntheticDataBadge } from "@/components/data/synthetic-data-badge";
import { EvidenceStatusBadge } from "@/components/data/status-badges";
import { ReconciliationDiff } from "@/components/reconciliation/reconciliation-diff";
import { BeforeAfterSummary } from "@/components/scenario/before-after-summary";
import { MaterialPredictionCard } from "@/components/upload/material-prediction-card";
import { UploadDropzone } from "@/components/upload/upload-dropzone";
import reconciliation from "@/lib/mocks/reconciliation.json";
import { ReconciliationResponse } from "@/lib/contracts";
import { ApiClientError } from "@/lib/errors";
import { computeScenario } from "@/lib/scenario-math";

afterEach(cleanup);
const finding = ReconciliationResponse.parse(reconciliation).findings[0];

describe("MaterialPredictionCard", () => {
  it("shows class + confidence and says it is not a legal category", () => {
    render(<MaterialPredictionCard result={{ predicted_class: "plastic", confidence: 0.94, uncertain: false, model_version: "mobilenetv3-v1" }} />);
    expect(screen.getByText("Plastic")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: /model confidence/i })).toHaveAttribute("aria-valuenow", "94");
    expect(screen.getByText(/not an official EPR or legal category/i)).toBeInTheDocument();
  });
  it("treats an uncertain result differently and asks for confirmation", () => {
    render(<MaterialPredictionCard result={{ predicted_class: "trash_other", confidence: 0.41, uncertain: true, model_version: "mobilenetv3-v1" }} />);
    expect(screen.getByText(/Uncertain/)).toBeInTheDocument();
    expect(screen.getByText(/confirm the material yourself/i)).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
  });
});

describe("ReconciliationDiff", () => {
  it("shows both original values and the difference", () => {
    render(<ReconciliationDiff finding={finding} />);
    expect(screen.getByTestId("diff-expected")).toHaveTextContent("0.5MT");
    expect(screen.getByTestId("diff-expected")).toHaveTextContent("= 500 kg");
    expect(screen.getByTestId("diff-observed")).toHaveTextContent("500,000 kg");
    expect(screen.getByTestId("diff-difference")).toHaveTextContent("499,500 kg (499.5 t)");
  });
  it("keeps the original visible beside an accepted correction", () => {
    render(<ReconciliationDiff finding={finding} accepted={{ action_id: "a", finding_id: finding.finding_id, kind: "accept_correction", actor: "x", timestamp: "2026-10-09T10:00:00Z", original_value_kg: 500000, proposed_value_kg: 500, reason: "Supplier confirmed" }} />);
    expect(screen.getByTestId("diff-observed")).toHaveTextContent("500,000 kg");
    expect(screen.getByTestId("diff-accepted")).toHaveTextContent("Supplier confirmed");
  });
});

describe("BeforeAfterSummary", () => {
  it("25 → 20 g over 100,000 units: 2,500 → 2,000 kg, reduction 500 kg", () => {
    render(<BeforeAfterSummary result={computeScenario({ units: 100000, baseline_g_per_unit: 25, proposed_g_per_unit: 20 })} />);
    expect(screen.getByTestId("baseline-kg")).toHaveTextContent("2,500 kg");
    expect(screen.getByTestId("proposed-kg")).toHaveTextContent("2,000 kg");
    expect(screen.getByTestId("reduction-kg")).toHaveTextContent("500 kg");
    expect(screen.getByText("Hypothetical", { selector: "span" })).toBeInTheDocument();
    expect(screen.getByText(/Not measured waste reduction/)).toBeInTheDocument();
  });
  it("says there is no change at 0%", () => {
    render(<BeforeAfterSummary result={computeScenario({ units: 1000, baseline_g_per_unit: 25, proposed_g_per_unit: 25 })} />);
    expect(screen.getByTestId("reduction-kg")).toHaveTextContent("0 kg");
    expect(screen.getByText(/No change in weight/)).toBeInTheDocument();
  });
});

describe("states", () => {
  it("every error explains what the user can do next", () => {
    const retry = vi.fn();
    render(<ErrorState error={new ApiClientError("x", "The CSV is missing columns.", "Add them and upload again.")} onRetry={retry} />);
    expect(screen.getByRole("alert")).toHaveTextContent("The CSV is missing columns.");
    expect(screen.getByRole("alert")).toHaveTextContent("What you can do: Add them and upload again.");
  });
  it("unexpected errors still carry a next step", () => {
    render(<ErrorState error={new Error("boom")} />);
    expect(screen.getByRole("alert")).toHaveTextContent(/What you can do/);
  });
  it("labels demo data and status distinctly", () => {
    render(<><SyntheticDataBadge /><EvidenceStatusBadge status="estimated" /><EvidenceStatusBadge status="needs_review" /><EvidenceStatusBadge status="document_supported" /></>);
    expect(screen.getByText("Synthetic demo data")).toBeInTheDocument();
    expect(screen.getByText("Estimated")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
  });
});

describe("UploadDropzone", () => {
  it("shows the rejection reason and next step returned by the handler", async () => {
    const onFile = vi.fn().mockResolvedValue({ ok: false, message: "“a.txt” is not a supported invoice pdf.", next_step: "Upload a .pdf file." });
    const { container } = render(<UploadDropzone kind="invoice" samples={[]} onFile={onFile} />);
    const input = container.querySelector('input[type="file"]') as HTMLInputElement;
    await userEvent.upload(input, new File(["x"], "a.txt", { type: "text/plain" }), { applyAccept: false });
    expect(await screen.findByRole("alert")).toHaveTextContent("What you can do: Upload a .pdf file.");
    expect(onFile).toHaveBeenCalledOnce();
  });
});
