import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // `BUILD_TARGET=lambda` (infrastructure/scripts/35-package-web.sh) emits a self-contained server for AWS Lambda.
  // Normal `npm run build` / `next start` are unaffected.
  ...(process.env.BUILD_TARGET === "lambda" ? { output: "standalone" as const } : {}),
};

export default nextConfig;
