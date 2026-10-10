export const INDUSTRIES = [
  "Beverages", "Food", "FMCG", "Personal Care", "Cosmetics", "Pharmaceuticals", "Household Products",
  "Electronics", "Appliances", "E-commerce", "Automotive", "Industrial Goods", "Retail", "Other",
] as const;

export const INDIAN_STATES = [
  "Andhra Pradesh", "Assam", "Bihar", "Chhattisgarh", "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh",
  "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Odisha", "Punjab", "Rajasthan",
  "Tamil Nadu", "Telangana", "Uttar Pradesh", "Uttarakhand", "West Bengal",
] as const;

export const PACKAGING_TYPES = [
  "PET bottles", "HDPE / PP caps and closures", "Flexible pouches / sachets", "Multi-layer laminates",
  "Corrugated cartons", "Glass bottles", "Paper labels", "Metal cans", "Rigid plastic tubs", "Not sure yet",
] as const;

export const ROLE_OPTIONS = [
  { id: "producer", label: "Producer", hint: "Makes plastic packaging or products packed in it." },
  { id: "manufacturer", label: "Manufacturer", hint: "Manufactures the packaged product." },
  { id: "importer", label: "Importer", hint: "Imports packaging or packaged products." },
  { id: "brand_owner", label: "Brand owner", hint: "Sells products under its own brand." },
] as const;

export const REGISTRATION_OPTIONS = [
  { id: "registered", label: "Registered on the CPCB portal" },
  { id: "in_progress", label: "Registration in progress" },
  { id: "not_registered", label: "Not registered" },
  { id: "unknown", label: "Unknown" },
] as const;
