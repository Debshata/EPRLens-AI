/**
 * Deterministic, versioned "potential applicability" hints for onboarding. Derived from the EPR handbook
 * self-assessment (secondary source, not verified law). It never says "compliant" and never gives a
 * legal determination — wording is always "potential … requires verification".
 */
import type { ApplicabilityOutcome, CompanyInput } from "./contracts";

export const APPLICABILITY_RULES_VERSION = "applicability-demo-v0";

export function assessApplicability(input: CompanyInput): ApplicabilityOutcome {
  const reasons: string[] = [];
  const missing: string[] = [];
  const roles = input.roles ?? [];
  const plasticPackaging = (input.packaging_types ?? []).some((p) => /plastic|pet|hdpe|pp|film|pouch|sachet/i.test(p));

  if (!roles.length && !input.roles_unknown) missing.push("Business role (producer, importer, brand owner, manufacturer)");
  if (input.roles_unknown) missing.push("Business role is marked Unknown");
  if (input.turnover_cr == null && !input.turnover_unknown) missing.push("Annual turnover (₹ crore)");
  if (input.turnover_unknown || input.turnover_cr == null) missing.push("Turnover is unknown — brand-owner threshold (₹50 crore per handbook) cannot be checked");
  if (!(input.states_operated ?? []).length) missing.push("Operating states");
  if (!(input.packaging_types ?? []).length) missing.push("Packaging types used");

  if (roles.includes("producer") || roles.includes("manufacturer")) reasons.push("Producers/manufacturers of plastic packaging are listed as obligated parties in the handbook.");
  if (roles.includes("importer")) reasons.push("Importers of plastic packaging or packaged products are listed as obligated parties.");
  if (roles.includes("brand_owner")) {
    if (input.turnover_cr != null && input.turnover_cr > 50) reasons.push("Brand owners with turnover above ₹50 crore are listed as obligated parties (threshold to be verified).");
    else if (input.turnover_cr != null) reasons.push("Brand owner below the ₹50 crore handbook threshold — verify the current rule before concluding.");
  }
  if (plasticPackaging) reasons.push("Plastic packaging is the only packaging material with an active EPR regime in the handbook.");

  const roleHit = roles.length > 0;
  let status: ApplicabilityOutcome["status"];
  if (!roleHit || !plasticPackaging) status = missing.length ? "needs_more_information" : "not_indicated";
  else status = "potentially_applicable";

  const statement =
    status === "potentially_applicable"
      ? "Potential applicability: plastic packaging EPR may apply — requires verification against official CPCB sources."
      : status === "needs_more_information"
        ? "Not enough information to indicate applicability. Complete the missing details or mark them Unknown."
        : "No plastic packaging EPR role indicated from the answers given — requires verification.";

  return { status, statement, reasons, missing, rules_version: APPLICABILITY_RULES_VERSION, legal_determination: false };
}
