#!/usr/bin/env bash
# Builds the Next.js app as a standalone server and packages it for AWS Lambda (+ Lambda Web Adapter layer). Output: build/web.zip
source "$(dirname "$0")/config.sh"
FE="$REPO_ROOT/frontend"
d="${BUILD_DIR:?}/pkg-web"

log "next build (BUILD_TARGET=lambda, live mode)"
( cd "$FE" && rm -rf .next && BUILD_TARGET=lambda NEXT_PUBLIC_API_MODE=live npm run build )

log "assemble package"
rm -rf "${d:?}"; mkdir -p "$d"
cp -R "$FE/.next/standalone/." "$d/"
mkdir -p "$d/.next" && cp -R "$FE/.next/static" "$d/.next/static"
[ -d "$FE/public" ] && cp -R "$FE/public" "$d/public"
# no local env files or secrets ever go into the package
find "$d" -maxdepth 2 -name '.env*' -type f -delete
rm -f "$d/tsconfig.tsbuildinfo"
printf '#!/bin/bash\nexec node server.js\n' > "$d/run.sh"; chmod +x "$d/run.sh"

rm -f "${BUILD_DIR:?}/web.zip"; (cd "$d" && zip -qr9 "${BUILD_DIR:?}/web.zip" .)
echo "web.zip  $(du -h "$BUILD_DIR/web.zip" | cut -f1) zipped, $(du -sh "$d" | cut -f1) unzipped (limit 250 MB unzipped)"
