import "server-only";
import { PutObjectCommand, S3Client } from "@aws-sdk/client-s3";
import { getSignedUrl } from "@aws-sdk/s3-request-presigner";
import type { UploadKind } from "../contracts";

const PREFIX: Record<UploadKind, string> = { csv: "csv", invoice: "invoices", image: "images" };

/** uploads/<company>/<kind>/<uuid>/<original-name>: the file name is preserved (sanitised) so results can show it. */
export function s3KeyFor(companyId: string, kind: UploadKind, id: string, fileName: string): string {
  const safeCompany = companyId.replace(/[^A-Za-z0-9_-]/g, "");
  const base = fileName.split(/[\\/]/).pop() ?? "file";
  const safeName = base.replace(/[^A-Za-z0-9._-]/g, "_").replace(/^\.+/, "").slice(-120) || "file";
  return `uploads/${safeCompany}/${PREFIX[kind]}/${id}/${safeName}`;
}

/** Short-lived (5 min) presigned PUT, pinned to the content type and exact size that passed validation. */
export async function presignPut(opts: { region: string; bucket: string; key: string; mime: string; size: number }): Promise<string> {
  const s3 = new S3Client({ region: opts.region });
  return getSignedUrl(s3, new PutObjectCommand({ Bucket: opts.bucket, Key: opts.key, ContentType: opts.mime, ContentLength: opts.size }), { expiresIn: 300 });
}
