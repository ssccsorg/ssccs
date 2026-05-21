# SSCCS Spike Runtime Validation - Environment Setup

## macOS

```bash
brew tap riscv-software-src/riscv
brew install riscv-tools
```

This installs spike (RISC-V ISA simulator), riscv-pk (proxy kernel),
and riscv-gnu-toolchain (cross-compiler) in one command.

## Linux (Docker)

From the repository root:

```bash
docker build -t ssccs-poc -f poc/Dockerfile .
docker run --rm -v "$(pwd):/workspace" ssccs-poc \
    bash -c "cd /workspace/poc/baremetal_riscv/simulation && bash run.sh --check"
```

Or using the root run.sh shortcut:

```bash
./run.sh --docker
```

## Verification

From `poc/baremetal_riscv/simulation/`:

```bash
bash run.sh --check
```

Or from the repository root:

```bash
./run.sh
```

Expected output:
```
=== SUMMARY ===
Passed: 30
Failed: 0
Total:  30
```
