#!/usr/bin/env bash
# Shared settings. Sourced by every script. Override with env vars, e.g. AWS_PROFILE=other PREFIX=eprlens-dev
set -euo pipefail

export AWS_PROFILE="${AWS_PROFILE:-eprlens}"
export AWS_REGION="${AWS_REGION:-ap-south-1}"
export AWS_DEFAULT_REGION="$AWS_REGION"
export AWS_PAGER=""
PREFIX="${PREFIX:-eprlens-demo}"

ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
UPLOADS_BUCKET="${PREFIX}-uploads-${ACCOUNT_ID}"
MODELS_BUCKET="${PREFIX}-models-${ACCOUNT_ID}"
TABLE="${PREFIX}-analysis"
FRONTEND_USER="${PREFIX}-frontend"
RUNTIME="python3.12"
ARCH="x86_64"
LOG_RETENTION_DAYS=3

# function dir name -> memory MB / timeout s (plain functions: macOS ships bash 3.2, no associative arrays)
FUNCTIONS="classify-image parse-invoice reconcile forecast detect-anomaly scenario-engine company-data"
memory_of()  { case "$1" in classify-image) echo 1536;; parse-invoice) echo 512;; reconcile) echo 512;; forecast) echo 1024;; detect-anomaly) echo 1024;; scenario-engine) echo 128;; company-data) echo 256;; esac; }
timeout_of() { case "$1" in classify-image) echo 30;; parse-invoice) echo 30;; reconcile) echo 30;; forecast) echo 60;; detect-anomaly) echo 60;; scenario-engine) echo 5;; company-data) echo 10;; esac; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BUILD_DIR="$REPO_ROOT/infrastructure/build"
fn_name() { echo "${PREFIX}-$1"; }
role_name() { echo "${PREFIX}-lambda-$1"; }
TAGS="Project=EPRLens,Env=demo"
log() { printf '\n==> %s\n' "$*"; }
