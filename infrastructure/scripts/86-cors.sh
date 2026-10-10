#!/usr/bin/env bash
# Allow the browser to PUT to presigned S3 URLs from the local frontend and from the Amplify domain.
#   ./86-cors.sh <amplify-default-domain>      e.g. d1abc2defg3.amplifyapp.com
source "$(dirname "$0")/config.sh"
DOMAIN="${1:?usage: 86-cors.sh <amplify-default-domain>}"
aws s3api put-bucket-cors --bucket "$UPLOADS_BUCKET" --cors-configuration "{\"CORSRules\":[{\"AllowedOrigins\":[\"http://localhost:3000\",\"http://localhost:3100\",\"https://*.$DOMAIN\"],\"AllowedMethods\":[\"PUT\"],\"AllowedHeaders\":[\"*\"],\"MaxAgeSeconds\":300}]}"
echo "CORS updated for https://*.$DOMAIN"
