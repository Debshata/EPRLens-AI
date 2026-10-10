export type ApiMode = "mock" | "live";

/** Switch with NEXT_PUBLIC_API_MODE=mock|live (default mock: no network, no AWS). */
export const API_MODE: ApiMode = process.env.NEXT_PUBLIC_API_MODE === "live" ? "live" : "mock";

export const SYNTHETIC_LABEL = "Synthetic demo data";
export const DISCLAIMER_SHORT = "Pre-compliance decision support — not a CPCB filing, certification or legal advice.";
