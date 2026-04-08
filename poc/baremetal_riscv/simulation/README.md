# OpenHW CORE‑V Simulation Environment

This directory contains notes and scripts for simulating SSCCS custom instructions on OpenHW CORE‑V cores.

## Required Tools

1. **riscvOVPsimCOREV** – Imperas reference simulator for OpenHW CORE‑V cores.
   - Download from [OpenHW Group](https://www.openhwgroup.org/) (member access may be required).
   - Alternatively, use the open‑source [OVPsim](https://github.com/riscv-ovpsim) with CORE‑V model plugins.

2. **RISC‑V Toolchain** – GCC compiler for RISC‑V (already covered by Rust target).
   - `riscv32-unknown-elf-gcc` for compiling C tests.

3. **OpenHW CORE‑V‑VERIF** – Verification environment (optional for simulation).
   - Contains testbenches and UVM components.

## Getting the Simulator

If you have OpenHW membership, you can access pre‑built binaries via the OpenHW portal. Otherwise, you can build the simulator from source:

```bash
git clone https://github.com/openhwgroup/core-v-verif
cd core-v-verif
make help
```

The simulation flow uses Makefiles and requires a licensed Imperas simulator (or the free OVPsim).

## Running a Simple Test

Once the simulator is available, we can compile a small RISC‑V program that uses custom instructions and run it.

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

## Integration with SSCCS

We plan to:

1. Write a Rust bare‑metal program that uses inline assembly for `custom1`/`custom2`.
2. Compile it to a RISC‑V ELF using `cargo build --target riscv32imac-unknown-none-elf`.
3. Convert the ELF to a binary memory image suitable for simulation.
4. Run the image on riscvOVPsimCOREV and capture the output.

## References

- [OpenHW CORE‑V‑VERIF GitHub](https://github.com/openhwgroup/core-v-verif)
- [Imperas OVPsim](https://www.imperas.com/riscv-ovpsim)
- [CORE‑V XIF Specification](https://github.com/openhwgroup/core-v-xif)