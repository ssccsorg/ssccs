#!/bin/bash
# Validate RISC-V assembly via QEMU (Linux only; macOS skips gracefully)
set -e

TARGET="riscv64gc-unknown-linux-gnu"

echo "=== RISC-V Assembly Validation ==="

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "  ⊘ Skipped (QEMU user-mode requires Linux)"
    echo "  Assembly validated through cargo check --target on Linux CI."
    exit 0
fi

# Install QEMU + target
if ! command -v qemu-riscv64 &>/dev/null; then
    sudo apt-get update -qq && sudo apt-get install -y -qq qemu-user
fi
rustup target add "$TARGET" 2>/dev/null || true

echo "  Target: $TARGET"
echo "  Building + testing under qemu-riscv64..."

cargo test --target "$TARGET" -- --test-threads=1 --nocapture 2>&1

echo ""
echo "  RISC-V assembly: VALIDATED via QEMU"
