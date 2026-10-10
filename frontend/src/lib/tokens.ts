/** Token constants for charts and Three.js (single source: mirrors :root in globals.css). */
export const TOKENS = {
  bg: "#030304",
  surface: "#0f1115",
  border: "#1e293b",
  muted: "#94a3b8",
  brand: "#22c55e",
  brandBright: "#86efac",
  brandDark: "#166534",
  info: "#38bdf8",
  caution: "#f59e0b",
  danger: "#ef4444",
} as const;

export const MATERIAL_COLORS: Record<string, string> = {
  PET: "#22c55e",
  HDPE: "#16a34a",
  PP: "#86efac",
  GLASS: "#38bdf8",
  CARDBOARD: "#a8a29e",
  PAPER: "#d6d3d1",
};
