# SSCCS Bare-Metal RISC-V Hardware Integration

Bare-metal (`no_std`) Rust crate for integrating SSCCS (Schema–Segment Composition Computing System) with RISC-V hardware, particularly targeting the OpenHW CORE-V ecosystem.

## Overview

This crate provides:

- **Custom RISC-V Instructions**: SSCCS observation primitives encoded as `custom1`/`custom2` opcodes
- **Software Emulation**: Host-compatible fallback for testing without hardware
- **XIF Interface Profile**: Stub for OpenHW CORE-V coprocessor integration
- **Zero-Overhead Abstraction**: Direct mapping from SSCCS concepts to hardware operations

## Target Platform

| Property | Value |
|----------|-------|
| **Architecture** | RISC-V 32-bit (RV32IMAC) |
| **Target Triple** | `riscv32imac-unknown-none-elf` |
| **ABI** | `none` (bare-metal, no OS) |
| **Panic Strategy** | `abort` |

## Relationship to Standard Workspace

This crate is **separate** from the `standard/` workspace:

| Aspect | `standard/` Workspace | `baremetal_riscv/` Crate |
|--------|----------------------|-------------------------|
| **Target** | Host (x86_64/aarch64) | RISC-V RV32IMAC |
| **Standard Library** | `std` available | `no_std` (core + alloc only) |
| **Panic Handler** | Default (unwind) | `panic-halt` (abort) |
| **Use Case** | Simulation, testing, benchmarking | Embedded hardware deployment |
 

## Installation

### Prerequisites

```bash
# Install Rust toolchain (if not already installed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Add RISC-V target
rustup target add riscv32imac-unknown-none-elf

# (Optional) Install cargo-binutils for object file inspection
rustup component add llvm-tools-preview
cargo install cargo-binutils
```

### Building

```bash
# Build for RISC-V target (release mode)
cargo build --target riscv32imac-unknown-none-elf --release

# Check without building (faster for development)
cargo check --target riscv32imac-unknown-none-elf

# Inspect the generated binary
cargo size --target riscv32imac-unknown-none-elf --release -- -A
```

### Rust Analyzer Configuration

For IDE support, add to `.vscode/settings.json`:

```json
{
  "rust-analyzer.cargo.target": "riscv32imac-unknown-none-elf"
}
```

## API Reference

### Core Functions

#### `observe_custom(scheme_id, field_id, rule_id) -> u32`

Software emulation of the SSCCS observation primitive. In hardware, this would be a `custom1` instruction.

```rust
use ssccs_baremetal_riscv::observe_custom;

// Perform observation (software emulation)
let result = unsafe { observe_custom(0x01, 0x02, 0x03) };
```

#### `observe_asm(scheme_id, field_id, rule_id) -> u32` (RISC-V only)

Inline assembly wrapper for the actual `custom1` instruction. Only available when compiling for `riscv32`.

```rust
#[cfg(target_arch = "riscv32")]
use ssccs_baremetal_riscv::observe_asm;

// Perform observation (hardware instruction)
let result = unsafe { observe_asm(0x01, 0x02, 0x03) };
```

### Instruction Encodings

The `instructions` module provides:

| Function | Description |
|----------|-------------|
| `encode_custom_rtype(rs3, rs2, rs1, funct3, opcode)` | Encode R-type custom instruction |
| `decode_custom(inst)` | Decode custom instruction fields |
| `observe_emulate(scheme_id, field_id, rule_id)` | Software emulation of OBSERVE |
| `collapse_emulate(scheme_id, segment_mask, field_id)` | Software emulation of COLLAPSE |

#### Custom Instruction Format

```
OBSERVE (custom1):
  31    27 26    20 19    15 14  12 11     7 6      0
  ┌──────┬────────┬────────┬─────┬─────────┬────────┐
  │  rs3 │  rs2   │  rs1   │funct3│ opcode  │  rd    │
  │scheme│ field  │  rule  │ 000 │ 0001011 │  (out) │
  └──────┴────────┴────────┴─────┴─────────┴────────┘
```

### Hardware Profile

#### `CoreVXifProfile`

Hardware profile for OpenHW CORE-V XIF (eXtension Interface) coprocessor integration.

```rust
use ssccs_baremetal_riscv::CoreVXifProfile;

let profile = CoreVXifProfile;
let result = profile.issue_observation(0x01, 0x02, 0x03);
```

## Research Goals

1. **Custom Instruction Implementation**: Map SSCCS observation primitives to RISC-V `custom1`/`custom2` opcodes
2. **CORE-V XIF Integration**: Develop coprocessor interface for offloading observation to hardware accelerator
3. **Simulation Validation**: Compare results with `standard/` workspace PoC using riscvOVPsimCOREV
4. **Verification IP**: Create testbenches for CORE-V-VERIF framework integration
5. **eFPGA Acceleration**: Explore QuickLogic fabric integration on CORE-V MCU DevKit
6. **OpenHW Contribution**: Upstream documentation and reference implementation

## Integration with OpenHW CORE-V

### Phase 1: Software Emulation (Current)

- Custom instruction encodings defined
- Software emulation functions implemented
- XIF interface stub created

### Phase 2: Verification IP

- [ ] CORE-V simulation integration
- [ ] Test suite for observation primitives
- [ ] Performance benchmarking against PoC

### Phase 3: Hardware Implementation

- [ ] XIF coprocessor design
- [ ] FPGA synthesis and bitstream generation
- [ ] Hardware validation on CORE-V MCU DevKit

## Links

- [SSCCS RISC-V Integration Research](../../docs/research/riscv.qmd)
- [OpenHW Integration Proposal](../../docs/proposal/openhw_integration.md)
- [OpenHW Group](https://www.openhwgroup.org/)
- [CORE-V XIF Specification](https://github.com/openhwgroup/core-v-xif)
- [Rust Embedded Book](https://docs.rust-embedded.org/book/)
- [Comprehensive Rust: Bare-Metal](https://google.github.io/comprehensive-rust/bare-metal/)

## License

This project is licensed under the same terms as the main SSCCS repository.
