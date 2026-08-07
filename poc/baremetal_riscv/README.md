# SSCCS Bare-Metal RISC-V Hardware Integration

Bare-metal (`no_std`) Rust crate for integrating SSCCS (Schema–Segment Composition Computing System) with RISC-V hardware, particularly targeting the OpenHW CORE-V ecosystem.

## Overview

This crate provides:

- **Custom RISC-V Instructions**: SSCCS observation primitives encoded as `custom1`/`custom2` opcodes
- **Software Fallback**: Host-compatible pure-Rust fallback for testing without RISC-V hardware
- **Golden Anchor Cross-Validation**: Automatically verified against SystemVerilog and a separate independent verification CLI (`ev`)
- **XIF Interface Profile**: Stub for OpenHW CORE-V coprocessor integration
- **Zero-Overhead Abstraction**: Direct mapping from SSCCS concepts to hardware operations

## Triple-Substrate Validation

The same constraint pipeline is independently implemented across **three computational substrates**, with automated cross-verification:

```
RISC-V Assembly (.S)  ──┐
                         ├── Golden Anchors (19, auto-verified by Python)
SystemVerilog (.sv)    ──┤
                         │
Rust Fallback          ──┘
```

The golden anchor system (`sv/check_golden_anchors.py`) reads constants from `observe_full.S` and checks them against `_golden_anchors.svh`. Any change to the assembly forces an anchor update, which forces the Python check to either pass or fail — keeping all three implementations in sync.

### ev (ExaVerif) Channel Verification

The open-source [ev](https://github.com/ssccsorg/ev) verification CLI independently reproduces the golden anchor results through its own constraint engine — a **fourth path** that cross-checks the triple-substrate validation:

```bash
git clone https://github.com/ssccsorg/ev
cd ev
bash scripts/demo-ssccs-poc.sh

# 5/5 channels match RISC-V assembly golden anchors:
#   narrow:   even ∧ range_0_10  →  2,REJECT,REJECT,10,REJECT
#   broad:    no constraints     →  2,3,5,10,12
#   sum3d_a:  (2,1,0)            →  3
#   sum3d_b:  (1,2,3)            →  6
#   parity:   {2,3}              →  0,1
```

## Target Reality

This crate has two distinct paths with different target requirements:

| Path | Target | Status |
|------|--------|--------|
| Rust fallback | Host (x86_64 / aarch64) | Default `cargo test` / `cargo build`, golden anchors verified |
| RISC-V assembly | RV64 (`riscv64-unknown-elf-*` toolchain) | All five `asm/*.S` modules assembled and executed under Spike + pk (`simulation/run.sh`): `observe_full.S` via `spike_test.c` and the concept harnesses, the other four via `asm_modules_test.c`; plus a syntax gate over all `asm/*.S` |
| Bare-metal cargo build | `riscv32imac-unknown-none-elf` | Blocked: the standard workspace crates (`ssccs-core`, `ssccs-primitive`) depend on std-only crates (`hex`, `serde` default, `thiserror`, `blake3` default). Tracked as a follow-up no_std refactor |

The assembly modules use RV64 instructions (`ld`/`sd`/`.8byte`). The reference simulation executes the assembly path at the ISA level via Spike, and the host path validates the same golden anchors through the Rust fallback.

## Target Platform

| Property | Value |
|----------|-------|
| **Architecture** | RISC-V 64-bit (RV64I + D, assembly path) / host for fallback |
| **Toolchain** | `riscv64-unknown-elf-*` (assembler, gcc, spike) |
| **Panic Strategy** | `abort` |

## Relationship to Standard Workspace

This crate is **separate** from the `standard/` workspace but shares its core types via dependency on `ssccs-core`.

| Aspect | `standard/` Workspace | `baremetal_riscv/` Crate |
|--------|----------------------|-------------------------|
| **Path** | Host (x86_64/aarch64) reference simulation | Host fallback + RV64 assembly under Spike |
| **Standard Library** | `std` | `std` on host; `no_std` intent for bare-metal targets (blocked, see Target Reality) |
| **Panic Handler** | Default (unwind) | `panic-halt` (abort) |
| **Use Case** | Simulation, testing, benchmarking | ISA-level assembly validation, hardware integration |

## Assembly Modules

Five hand-written RISC-V assembly files implement the SSCCS observation pipeline with branchless, constant-time constraint primitives:

| Module | File | Functions |
|--------|------|-----------|
| **Observe** | `asm/observe_full.S` | Constraints (`ck_even`, `ck_range`, `ck_eq_val`, `ck_gt`), composition (`compose_and`, `compose_or`, `compose_intersect`, `compose_union`, `compose_product_2d`), projectors (`proj_id`, `proj_sum2d`, `proj_sum3d`, `proj_parity`, `proj_negate`), `observe()` hot path, batch mode, narrow/broad scenario, generated-table observation (`observe_scheme` over `SCHEME_SEG_COUNT`/`SCHEME_COORDS`, consumed with the standard workspace `asm_emitter` output) |
| **Collapse** | `asm/collapse.S` | `collapse_sum`, `collapse_min`, `collapse_max`, `collapse_product`, `collapse_count`, `collapse_weighted_sum`, `collapse_weighted_avg` |
| **Field Update** | `asm/field_update.S` | `field_add_constraint`, `field_remove_constraint`, `field_clear`, `field_add_transition`, `field_update_weight`, `field_get_transitions` |
| **Scheme Layout** | `asm/scheme_layout.S` | `layout_linear_1d`, `layout_linear_nd`, `layout_row_major_2d`, `layout_row_major_3d`, `layout_col_major_2d`, `morton_encode_2d`, `layout_zorder_2d` |
| **Scheme Adjacency** | `asm/scheme_adjacency.S` | `adj_grid_4`, `adj_grid_8`, `adj_manhattan_1d`, `adj_graph_edges` |

## SystemVerilog Modules

18 SystemVerilog modules independently implement the same pipeline:

- **Constraints** (5): `ck_eq`, `ck_even`, `ck_gt`, `ck_range`, `ck_range_010`
- **Projectors** (5): `proj_identity`, `proj_negate`, `proj_parity`, `proj_sum2d`, `proj_sum3d`
- **Composition** (3): `compose_intersect`, `compose_product_2d`, `compose_union`
- **Pipeline**: `observe`, `ssccs_xif_coprocessor`, `scenario_narrow_broad_tb`, `xif_integration_tb`
- **Testbench**: `composition_tb`

## Test Suite

All tests pass on host (x86_64/aarch64) via the Rust fallback, and can be cross-compiled for RISC-V targets:

```bash
# Host fallback tests
cargo test

# RISC-V assembly golden anchor verification (host)
cargo test -- test_observe_golden_anchors
cargo test -- test_collapse_golden_anchors
cargo test -- test_field_update_golden_anchors
cargo test -- test_layout_golden_anchors
cargo test -- test_adjacency_golden_anchors
```

## Research Goals

1. **Custom Instruction Implementation**: Map SSCCS observation primitives to RISC-V `custom1`/`custom2` opcodes
2. **CORE-V XIF Integration**: Develop coprocessor interface for offloading observation to hardware accelerator
3. **Simulation Validation**: Compare results with Rust fallback using riscvOVPsimCOREV
4. **Verification IP**: Create testbenches for CORE-V-VERIF framework integration
5. **eFPGA Acceleration**: Explore QuickLogic fabric integration on CORE-V MCU DevKit
6. **OpenHW Contribution**: Upstream documentation and reference implementation

## Integration with OpenHW CORE-V

### Phase 1: Software Emulation (Complete)

- Custom instruction encodings defined
- Software emulation functions implemented
- XIF interface stub created
- Triple-substrate cross-validation operational (Rust ↔ Assembly ↔ SystemVerilog)
- **ev channel demo verifies all golden anchors independently**

### Phase 2: Verification IP (Next)

- [ ] CORE-V simulation integration
- [ ] ev YAML schemas for CORE-V XIF instructions
- [ ] cocotb/Verilator integration for ev ↔ simulation cross-verification

### Phase 3: Hardware Implementation

- [ ] XIF coprocessor design
- [ ] FPGA synthesis and bitstream generation
- [ ] Hardware validation on CORE-V MCU DevKit

## Links

- [ev (ExaVerif)](https://github.com/ssccsorg/ev) — open-source exhaustive verification CLI
- [SSCCS RISC-V Integration Research](/docs/research/riscv.qmd)
- [OpenHW Integration Proposal](/docs/partnerships/openhw_integration.md)
- [OpenHW Group](https://www.openhwgroup.org/)
- [CORE-V XIF Specification](https://github.com/openhwgroup/core-v-xif)
- [Rust Embedded Book](https://docs.rust-embedded.org/book/)
- [Comprehensive Rust: Bare-Metal](https://google.github.io/comprehensive-rust/bare-metal/)

## License

This project is licensed under the same terms as the main SSCCS repository. Apache 2.0.
