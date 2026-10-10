import { randomUUID } from "node:crypto";
import { NextResponse } from "next/server";
import { z } from "zod";
import { UploadKind } from "@/lib/contracts";
import { validateFileMeta } from "@/lib/upload-validation";
import { serverEnv } from "@/lib/server/env";
import { apiError, liveGuard, toErrorResponse } from "@/lib/server/http";
import { presignPut, s3KeyFor } from "@/lib/server/presign";

export const runtime = "nodejs";

const Body = z.object({ company_id: z.string().min(1), kind: UploadKind, name: z.string().min(1), size: z.number().int().positive(), mime: z.string(), sha256: z.string().length(64) });

export async function POST(req: Request) {
  const blocked = liveGuard();
  if (blocked) return blocked;
  try {
    const b = Body.safeParse(await req.json().catch(() => null));
    if (!b.success) return apiError(400, "invalid_request", "The upload request is not valid.", "Choose the file again and retry.");
    const check = validateFileMeta(b.data.kind, { name: b.data.name, size: b.data.size, type: b.data.mime });
    if (!check.ok) return apiError(400, "file_rejected", check.message, check.next_step);
    const env = serverEnv();
    const key = s3KeyFor(b.data.company_id, b.data.kind, randomUUID(), b.data.name);
    const upload_url = await presignPut({ region: env.AWS_REGION, bucket: env.UPLOADS_BUCKET, key, mime: b.data.mime, size: b.data.size });
    return NextResponse.json({ upload_url, s3_key: key });
  } catch (e) {
    return toErrorResponse(e);
  }
}
