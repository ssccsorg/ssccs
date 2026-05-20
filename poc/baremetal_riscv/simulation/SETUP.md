# SSCCS Spike Runtime Validation - Environment Setup

## macOS

```bash
brew tap riscv-software-src/riscv
brew install riscv-tools
```

This installs spike (RISC-V ISA simulator), riscv-pk (proxy kernel),
and riscv-gnu-toolchain (cross-compiler) in one command.

## Linux (Docker)

```bash
docker build -t ssccs-poc -f ../../Dockerfile ../../
docker run --rm -v $(pwd)/../..:/workspace ssccs-poc bash -c "cd /workspace/poc/baremetal_riscv/simulation && ./run.sh --check"
```

Or build directly with prerequisites installed per the Dockerfile.

## Verification

```bash
./run.sh --check
```

Expected output:
```
=== SUMMARY ===
Passed: 30
Failed: 0
Total:  30
```
