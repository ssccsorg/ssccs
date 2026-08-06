#!/bin/bash
#
# SSCCS Reference Simulation Benchmark Runner
#
# Runs the single-file bench suite (bench.rs): the verify group (path
# equality guard) and the kernels group (baseline vs SSCCS measurements).
# Results are captured with a timestamp and commit hash into result/.
#
# Usage:
#   ./run.sh                 # full run: verify + kernels
#   ./run.sh --quick         # reduced measurement time (CI)
#   ./run.sh --check         # exit nonzero on any phase failure
#   ./run.sh --quick --check # CI gate: fast + strict

set -e

MODE="run"
QUICK=""

for arg in "$@"; do
    case "$arg" in
        --check) MODE="check" ;;
        --quick) QUICK="1" ;;
        *) echo "Usage: $0 [--check] [--quick]"; exit 1 ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULT_DIR="$SCRIPT_DIR/result"
mkdir -p "$RESULT_DIR"

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
COMMIT_HASH=$(git -C "$SCRIPT_DIR/.." rev-parse --short HEAD 2>/dev/null || echo unknown)
OUT="$RESULT_DIR/output-${TIMESTAMP}.txt"

QUICK_FLAG=""
[ "$QUICK" = "1" ] && QUICK_FLAG="--quick"

echo "=== SSCCS Reference Simulation Benchmarks ==="
echo "Timestamp: $TIMESTAMP"
echo "Commit:    $COMMIT_HASH"
echo ""

PASSED=0
FAILED=0

# ── Phase 1: verify (correctness guard) ──
echo "── Phase 1: verify (path equality) ──"
set +e
cargo bench --bench bench -- verify $QUICK_FLAG 2>&1 | tee "$OUT"
STATUS=$?
set -e
if [ $STATUS -eq 0 ]; then
    echo "  Verify: PASSED"
    PASSED=$((PASSED + 1))
else
    echo "  Verify: FAILED (exit $STATUS)"
    FAILED=$((FAILED + 1))
fi
echo ""

# ── Phase 2: kernels (measurements) ──
echo "── Phase 2: kernels (baseline vs ssccs) ──"
set +e
cargo bench --bench bench -- kernels $QUICK_FLAG 2>&1 | tee -a "$OUT"
STATUS=$?
set -e
if [ $STATUS -eq 0 ]; then
    echo "  Kernels: PASSED"
    PASSED=$((PASSED + 1))
else
    echo "  Kernels: FAILED (exit $STATUS)"
    FAILED=$((FAILED + 1))
fi
echo ""

# ── Summary ──
echo "============================================"
echo "  Results: $PASSED passed, $FAILED failed"
echo "============================================"
echo ""
echo "=== Measured times (ns unless noted) ==="
grep -E "time:" "$OUT" || true
echo ""
echo "Raw output:  $OUT"

if [ "$MODE" = "check" ] && [ $FAILED -gt 0 ]; then
    exit 1
fi
