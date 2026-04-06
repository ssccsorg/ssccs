# SSCCS Proof of Concept (PoC)

This repository contains a proof‑of‑concept implementation of the **Schema–Segment Composition Computing System (SSCCS)**, a new computational model that redefines computation as the observation of structured potential rather than as a sequence of state mutations.

The PoC demonstrates the core ontological layers of SSCCS:
- **Segment** – immutable coordinate points in a multi‑dimensional possibility space.
- **Scheme** – immutable structural blueprint defining axes, segments, relations, memory layout, and observation rules.
- **Field** – mutable container of dynamic constraints.
- **Projector** – semantic interpreter that observes a combination of Field and Segment to produce a projection.
- **Observation** – the sole active event that collapses admissible configurations into a deterministic projection.

The implementation is written in Rust and serves as a reference for the software‑emulation phase (Phase 1) of the SSCCS roadmap.

## Quick Start

### Prerequisites

- Rust toolchain (stable) with [rustup](https://rustup.rs/)
- For bare-metal RISC-V development: `rustup target add riscv32imac-unknown-none-elf`

### Build and Run

```bash
# Navigate to poc directory
cd poc

# Build all workspaces
./run.sh --validation

# Or run in development mode (applies formatting first)
./run.sh --run
```

### Validation Script

The `run.sh` script automatically discovers all Rust workspaces and standalone crates, then performs:

1. **Formatting check** (`cargo fmt --check`)
2. **Linting** (`cargo clippy --workspace -- -D warnings`) - skips bare-metal
3. **Build** (`cargo build --workspace --release`) - skips bare-metal
4. **Tests** (`cargo test --workspace --all-targets --release`)
5. **Binary execution** - discovers and runs all binary crates

```bash
# Validation mode (recommended for CI)
./run.sh --validation

# Development mode (applies formatting)
./run.sh --run
```

## Workspaces

### `standard/` - Standard Workspace

The main workspace containing all host-compatible (std) crates:

| Category | Crates |
|----------|--------|
| **Core Infrastructure** | `core`, `primitive`, `schemes`, `examples` |
| **Research Placeholders** | `hardware-mapping`, `field-synthesis`, `compiler-opt` |
| **Experiments** | `experiment-01-segment` through `experiment-10-integrated`, `data-processing` |

See [`standard/README.md`](standard/README.md) for detailed documentation.

### `baremetal_riscv/` - Bare-Metal RISC-V Crate

A standalone crate for RISC-V bare-metal hardware integration:

- **Target**: `riscv32imac-unknown-none-elf`
- **Features**: `no_std`, custom RISC-V instructions (`custom1`/`custom2`)
- **Purpose**: SSCCS observation primitives for OpenHW CORE-V ecosystem

See [`baremetal_riscv/README.md`](baremetal_riscv/README.md) for detailed documentation.

## Dependency Graph

```
ssccs-core (no internal dependencies - absolute primitives)
    │
    ▼
ssccs-primitive (depends on ssccs-core)
    │
    ├──────────────┐
    ▼              ▼
ssccs-schemes   ssccs-examples (both depend on ssccs-primitive + ssccs-core)
    │              │
    └──────┬───────┘
           │
           ▼
    experiment-* crates (depend on ssccs-schemes, ssccs-examples, ssccs-primitive, ssccs-core)
```

## Why Rust Was Chosen for the PoC

Rust was selected for several reasons:

1. **Memory Safety Without Garbage Collection** – SSCCS relies on precise control over memory layout and immutability guarantees that Rust's ownership system provides at compile time.

2. **Zero-Cost Abstractions** – The Scheme abstraction layer and Projector traits introduce no runtime overhead compared to hand-written code.

3. **Immutability by Default** – Segments and Schemes are immutable by design, aligning with Rust's emphasis on immutable data structures.

4. **Type System Expressiveness** – Rust's type system enables encoding SSCCS ontological distinctions (Segment vs. Scheme vs. Field) at the type level, preventing category errors at compile time.

5. **Cryptographic Primitives** – The BLAKE3 hashing library provides efficient cryptographic identity computation for Segments and Schemes.

6. **Bare-Metal Support** – Rust's `no_std` ecosystem enables seamless transition from host simulation to embedded RISC-V targets.

## Architecture Overview

### Core Ontological Layers

| Layer | Description | Crate |
|-------|-------------|-------|
| **Segment** | Immutable coordinate point with cryptographic identity | `ssccs-core` |
| **Field** | Mutable container of dynamic constraints | `ssccs-core` |
| **Scheme** | Immutable structural blueprint | `ssccs-primitive` |
| **Projector** | Semantic interpreter for Segment-Field pairs | `ssccs-core` (trait), `ssccs-examples` (implementations) |
| **Observation** | Active event that collapses potential to projection | `ssccs-core` |

### Scheme Templates

| Template | Description | Use Case |
|----------|-------------|----------|
| `Grid2DTemplate` | 2D grid with configurable topology | Spatial computation, cellular automata |
| `IntegerLineTemplate` | 1D linear scheme | Integer arithmetic, sequences |
| `GraphTemplate` | Arbitrary node-edge structure | Network analysis, relational data |
| `Tensor3DTemplate` | 3D tensor scheme | Multi-dimensional computation |
| `CompositeScheme` | Composition of multiple schemes | Complex hierarchical structures |
| `TransformedScheme` | Geometric transformations | Rotation, scaling, translation |

## Local CI Validation with Act

You can run the same CI workflow locally using [act](https://github.com/nektos/act):

```bash
# Install act
brew install act  # macOS
# or
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash  # Linux

# Run the validation job
cd poc
act -j rust-check -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

## License

This project is licensed under the same terms as the main SSCCS repository.

## Contributing

See the main repository's [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
