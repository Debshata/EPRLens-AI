#!/usr/bin/env bash
# Creates: 2 private S3 buckets (uploads, models) and 1 DynamoDB table (PAY_PER_REQUEST). Idempotent.
source "$(dirname "$0")/config.sh"

make_bucket() {
  local b="$1"
  if aws s3api head-bucket --bucket "$b" 2>/dev/null; then echo "bucket exists: $b"; else
    aws s3api create-bucket --bucket "$b" --region "$AWS_REGION" --create-bucket-configuration "LocationConstraint=$AWS_REGION" >/dev/null
    echo "created bucket: $b"
  fi
  aws s3api put-public-access-block --bucket "$b" --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
  aws s3api put-bucket-encryption --bucket "$b" --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
  aws s3api put-bucket-tagging --bucket "$b" --tagging "TagSet=[{Key=Project,Value=EPRLens},{Key=Env,Value=demo}]"
  aws s3api put-bucket-policy --bucket "$b" --policy "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"DenyInsecureTransport\",\"Effect\":\"Deny\",\"Principal\":\"*\",\"Action\":\"s3:*\",\"Resource\":[\"arn:aws:s3:::$b\",\"arn:aws:s3:::$b/*\"],\"Condition\":{\"Bool\":{\"aws:SecureTransport\":\"false\"}}}]}"
}

log "S3 buckets (private, encrypted, TLS-only)"
make_bucket "$UPLOADS_BUCKET"
make_bucket "$MODELS_BUCKET"

log "Uploads bucket: expire demo uploads after 7 days; CORS for presigned PUT from the local frontend"
aws s3api put-bucket-lifecycle-configuration --bucket "$UPLOADS_BUCKET" --lifecycle-configuration '{"Rules":[{"ID":"expire-demo-uploads","Status":"Enabled","Filter":{"Prefix":"uploads/"},"Expiration":{"Days":7},"AbortIncompleteMultipartUpload":{"DaysAfterInitiation":1}}]}'
aws s3api put-bucket-cors --bucket "$UPLOADS_BUCKET" --cors-configuration '{"CORSRules":[{"AllowedOrigins":["http://localhost:3000","http://localhost:3100"],"AllowedMethods":["PUT"],"AllowedHeaders":["*"],"MaxAgeSeconds":300}]}'

log "DynamoDB table $TABLE (on-demand)"
if aws dynamodb describe-table --table-name "$TABLE" >/dev/null 2>&1; then echo "table exists"; else
  aws dynamodb create-table --table-name "$TABLE" --billing-mode PAY_PER_REQUEST \
    --attribute-definitions AttributeName=pk,AttributeType=S AttributeName=sk,AttributeType=S \
    --key-schema AttributeName=pk,KeyType=HASH AttributeName=sk,KeyType=RANGE \
    --tags Key=Project,Value=EPRLens Key=Env,Value=demo >/dev/null
  aws dynamodb wait table-exists --table-name "$TABLE"
fi
echo "done: $UPLOADS_BUCKET, $MODELS_BUCKET, $TABLE"
