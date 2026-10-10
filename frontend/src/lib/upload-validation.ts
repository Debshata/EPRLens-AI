import type { UploadKind } from "./contracts";
import { formatBytes } from "./formatters";

export interface UploadRule {
  kind: UploadKind;
  label: string;
  accept: string;
  extensions: string[];
  mimes: string[];
  maxBytes: number;
  helper: string;
}

export const UPLOAD_RULES: Record<UploadKind, UploadRule> = {
  csv: {
    kind: "csv",
    label: "Transaction CSV",
    accept: ".csv,text/csv",
    extensions: [".csv"],
    mimes: ["text/csv", "application/vnd.ms-excel", "text/plain", ""],
    maxBytes: 5 * 1024 * 1024,
    helper: "CSV up to 5 MB with columns transaction_id, company_id, date, raw_quantity, raw_unit.",
  },
  invoice: {
    kind: "invoice",
    label: "Invoice PDF",
    accept: ".pdf,application/pdf",
    extensions: [".pdf"],
    mimes: ["application/pdf"],
    maxBytes: 10 * 1024 * 1024,
    helper: "Text-based (digital) PDF up to 10 MB. Scanned images are not supported yet.",
  },
  image: {
    kind: "image",
    label: "Packaging photo",
    accept: ".jpg,.jpeg,.png,image/jpeg,image/png",
    extensions: [".jpg", ".jpeg", ".png"],
    mimes: ["image/jpeg", "image/png"],
    maxBytes: 8 * 1024 * 1024,
    helper: "JPG or PNG up to 8 MB. The result is a probable material only, not an official EPR category.",
  },
};

export type FileCheck = { ok: true } | { ok: false; message: string; next_step: string };

export function validateFileMeta(kind: UploadKind, file: { name: string; size: number; type: string }): FileCheck {
  const rule = UPLOAD_RULES[kind];
  const ext = file.name.includes(".") ? file.name.slice(file.name.lastIndexOf(".")).toLowerCase() : "";
  if (file.size === 0) {
    return { ok: false, message: `"${file.name}" is empty (0 bytes).`, next_step: "Export the file again from its source and make sure it has content." };
  }
  if (!rule.extensions.includes(ext) || !rule.mimes.includes(file.type)) {
    return {
      ok: false,
      message: `"${file.name}" is not a supported ${rule.label.toLowerCase()} (${ext || "no extension"}${file.type ? `, ${file.type}` : ""}).`,
      next_step: `Upload a ${rule.extensions.join(" / ")} file.`,
    };
  }
  if (file.size > rule.maxBytes) {
    return {
      ok: false,
      message: `"${file.name}" is ${formatBytes(file.size)}; the limit is ${formatBytes(rule.maxBytes)}.`,
      next_step: "Reduce the file size (split the CSV by month or compress the image) and upload again.",
    };
  }
  return { ok: true };
}
