#!/bin/bash
set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Global test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper: run a command and check exit status
run_test() {
    local name="$1"
    shift
    echo -e "${YELLOW}▶ Running: $name${NC}"
    if "$@"; then
        echo -e "${GREEN}✓ $name passed${NC}"
        ((TESTS_PASSED++))
        return 0
    else
        echo -e "${RED}✗ $name failed${NC}"
        ((TESTS_FAILED++))
        return 1
    fi
}

# Clean up any previous test artifacts
cleanup() {
    rm -rf /tmp/act-artifacts
    echo "Cleaned up /tmp/act-artifacts"
}

# Trap to show summary even on early exit
trap 'echo -e "\n${YELLOW}========== TEST SUMMARY ==========${NC}"; echo "Passed: $TESTS_PASSED"; echo "Failed: $TESTS_FAILED"; if [ $TESTS_FAILED -gt 0 ]; then exit 1; else exit 0; fi' EXIT

cleanup

# ----------------------------------------------------------------------
# Test 2: Rust POC CI (check-poc.yml, job=check-poc)
# ----------------------------------------------------------------------
run_test "Rust POC CI" \
    act -W .github/workflows/check-poc.yml

# ----------------------------------------------------------------------
# Test 3: Build documentation (deploy-docs-ghpage.yml, job=build)
# ----------------------------------------------------------------------
run_test "Documentation build (Quarto site)" \
    act -W .github/workflows/deploy-docs-ghpage.yml \
        --job build \
        --bind \
        --env CI=true \
        --rm \
        --container-architecture linux/amd64 \
        --platform ubuntu-latest=catthehacker/ubuntu:act-24.04 \
        --artifact-server-path "/tmp/act-artifacts"

# Summary printed automatically via EXIT trap