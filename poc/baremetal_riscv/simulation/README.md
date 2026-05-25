# OpenHW CORE-V Simulation Environment

This directory contains notes and scripts for simulating SSCCS custom instructions on OpenHW CORE-V cores.

## Current Status: Pre-Simulation

Simulation infrastructure is not yet set up. The current validation relies on:

1. **Host fallback tests** — `cargo test` runs all SSCCS pipeline tests on x86_64/aarch64
2. **Golden anchor cross-verification** — Python script checks RISC-V assembly constants against SystemVerilog
3. **ev (ExaVerif) channel demo** — independent CLI reproduces golden anchors via its own constraint engine

Actual RISC-V simulation on riscvOVPsimCOREV or Verilator is the next step.

## Required Tools

1. **riscvOVPsimCOREV** — Imperas reference simulator for OpenHW CORE-V cores.
   - Download from [OpenHW Group](https://www.openhwgroup.org/) (member access may be required).
   - Alternatively, use the open-source [OVPsim](https://github.com/riscv-ovpsim) with CORE-V model plugins.

2. **RISC-V Toolchain** — GCC compiler for RISC-V.
   - `riscv32-unknown-elf-gcc` for compiling C tests.

3. **Verilator** — Open-source SystemVerilog simulator (for ev integration).
   - `apt install verilator` or `brew install verilator`

4. **(Optional) OpenHW CORE-V-VERIF** — Verification environment.
   - Contains testbenches and UVM components. Not required for simulation-only flow.

## Getting the Simulator

If you have OpenHW membership, you can access pre-built binaries via the OpenHW portal. Otherwise, you can build from source:

```bash
git clone https://github.com/openhwgroup/core-v-verif
cd core-v-verif
make help
```

The simulation flow uses Makefiles and requires a licensed Imperas simulator (or the free OVPsim).

## Planned Integration with ev (ExaVerif)

Once the simulator is available, the integration with [ev](https://github.com/ssccsorg/ev) follows this flow:

```
1. ev generates all valid constraint combinations (YAML → expand → observe)
2. Each combination maps to a RISC-V instruction test case
3. Simulator runs the test case on CORE-V core model
4. Simulator output is compared against ev's prediction
5. Any mismatch indicates either a bug in ev or a simulator configuration issue
```

This is the same channel verification pattern that ev already uses against the RISC-V assembly golden anchors — extended to cover the CORE-V simulation environment.

## Running a Simple Test (When Simulator Is Available)

Example program (`test_custom.S`):

```assembly
.section .text
.global _start
_start:
    li a0, 0x1234   # scheme_id
    li a1, 0x5678   # field_id
    li a2, 0x9ABC   # rule_id
    custom1 a3, a0, a1, a2   # OBSERVE custom instruction
    ebreak
```

Compile with:

```bash
riscv32-unknown-elf-gcc -nostartfiles -march=rv32imc -mabi=ilp32 -o test.elf test_custom.S
```

Run with the simulator:

```bash
riscvOVPsimCOREV --program test.elf --variant CV32E40P
```

## References

- [ev (ExaVerif)](https://github.com/ssccsorg/ev) — open-source exhaustive verification CLI
- [SSCCS Bare-Metal README](../README.md)
- [OpenHW CORE-V-VERIF GitHub](https://github.com/openhwgroup/core-v-verif)
- [Imperas OVPsim](https://www.imperas.com/riscv-ovpsim)
- [CORE-V XIF Specification](https://github.com/openhwgroup/core-v-xif)
