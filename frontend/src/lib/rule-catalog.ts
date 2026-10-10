/** Plain-language names for rule ids (from the anomaly catalogue / rules_config.json, rules-v1). */
export const RULE_CATALOG: Record<string, { title: string; description: string }> = {
  QTY_MATCH_TOL: { title: "Quantity match", description: "Invoice and linked record must agree within 0.05% (or 0.01 kg)." },
  QTY_RATIO_POW10: { title: "Power-of-ten ratio", description: "The two quantities differ by exactly 10, 100 or 1,000× — a typical decimal or extra-zero slip." },
  UNIT_MISMATCH: { title: "Unit conversion", description: "A unit (for example tonne vs kg) appears to have been applied incorrectly." },
  DUP_COMPOSITE_KEY: { title: "Duplicate invoice", description: "Same supplier, number, date, amount and lines entered twice. Invoice number alone is never used." },
  RECYCLED_LE_COLLECTED: { title: "Recycled ≤ collected", description: "In this synthetic cohort, recycled quantity should not exceed collected quantity." },
  CATEGORY_MASTER_MATCH: { title: "Category vs product master", description: "The printed plastic category should match the product master (a synthetic convention; legal status to be verified)." },
  REQUIRED_FIELDS: { title: "Required fields", description: "Quantity, unit, date and category must be present." },
};

export function ruleTitle(id: string): string {
  return RULE_CATALOG[id]?.title ?? id;
}
