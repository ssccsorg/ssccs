# SSCCS Proof of Concept (PoC)

This repository contains a proof‑of‑concept implementation of the **Schema–Segment Composition Computing System (SSCCS)**, a new computational model that redefines computation as the observation of structured potential rather than as a sequence of state mutations.

The PoC demonstrates the core ontological layers of SSCCS:

- **Segment** – immutable coordinate points in a multi‑dimensional possibility space.
- **Scheme** – immutable structural blueprint defining axes, segments, relations, memory layout, and observation rules.
- **Field** – mutable container of dynamic constraints.
- **Projector** – semantic interpreter that observes a combination of Field and Segment to produce a projection.
- **Observation** – the sole active event that collapses admissible configurations into a deterministic projection.

The implementation is written in Rust and serves as a reference for the software‑emulation phase (Phase 1) of the SSCCS roadmap.

## Workspace Structure

The PoC is organized as a **Rust workspace** with multiple crates, enabling independent development of distinct research tracks while sharing a common core.

### Core Infrastructure Crates

| Crate | Purpose |
|-------|---------|
| **`ssccs-core`** | Absolute primitives: `Segment`, `Coordinates`, `Constraint`, `Field`, `TransitionMatrix`, `Projector` trait, and observation functions. |
| **`ssccs-primitive`** | Scheme abstraction layer: `Scheme`, `SchemeBuilder`, `SchemeTrait`, structural relations, constraints, observation rules, and memory layout abstractions. |
| **`ssccs-schemes`** | Concrete Scheme implementations and developer input types: `Grid2DTemplate`, `IntegerLineTemplate`, `GraphTemplate`, `Tensor3DTemplate`, `CompositeScheme`, `TransformedScheme`, `BooleanSpace`, `IntegerSpace`. |
| **`ssccs-examples`** | Shared utilities for experiments: projector implementations (`IntegerProjector`, `ArithmeticProjector`, `ParityProjector`, `CoordinateSumProjector`), compiler pipeline, `.ss` binary parser, assembly data emitter, branchless constraint gate emitter, and test constraints. |

### Standalone Benchmark Crate

The validation-only benchmark suite lives outside this workspace at [`/poc/benches/`](../benches/): a standalone criterion crate (`ssccs-benchmarks`) with a single `bench.rs` expressing the three kernels (vector addition, 2D convolution, graph BFS) as both a pure Rust baseline and an SSCCS Scheme + Field + Projector formulation. Run it manually with `benches/run.sh`; it is not part of the default `poc/run.sh` validation or CI.

### Experiment Crates (Constitutional Concept Tests)

Each experiment crate contains an independent constitutional concept test that can be run, tested, and evolved separately:

| Crate | Test |
|-------|------|
| **`concept-segment`** | Segment concept - immutable coordinate points with cryptographic identity |
| **`concept-field`** | Field concept - mutable constraint container with transitions |
| **`concept-projector`** | Projector concept - semantic interpretation of Segment-Field pairs |
| **`concept-observation`** | Observation concept - active event collapsing potential to projection |
| **`concept-space`** | Space concept - developer input types (Boolean, Integer) |
| **`concept-scheme`** | Scheme concept - structural blueprint with axes and relations |
| **`concept-adjacency`** | Adjacency memory - structural neighbor relationships |
| **`concept-composite`** | Composite & Transformed Schemes - scheme composition and geometric transformation |
| **`concept-transition`** | Transition Matrix - weighted directed graph for relational topology |
| **`concept-integrated`** | Integrated Workflow - complete SSCCS pipeline demonstration |

### Research Placeholder Crates

| Crate | Purpose |
|-------|---------|
| **`ssccs-field-synthesis`** | Placeholder for research on Field composition algebra and synthesis techniques. |
| **`ssccs-hardware-mapping`** | Placeholder for research on mapping Schemes to hardware (CPU, FPGA, PIM). |
| **`ssccs-hardware-integration`** | **Standard (std)** hardware abstraction layer for SSCCS observation. |
| **`ssccs-compiler-opt`** | Placeholder for research on compiler optimisations and open-format-to-machine-code compilation. |

All crates reside under `poc/crates/`. The experiment crates are organized under `poc/crates/concepts/`. The workspace configuration is defined in `poc/Cargo.toml`.

### Related Research (Separate Workspaces)

| Directory | Purpose | Target |
|-----------|---------|--------|
| **`research/baremetal_hw/`** | Bare-metal RISC-V hardware integration with custom instructions | `riscv32imac-unknown-none-elf` (`no_std`) |
| **`poc/crates/hardware-integration/`** | Standard hardware abstraction layer (host-compatible) | Host (`std`) |

## Dependency Graph

```text
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
    experiment-* crates (under crates/concepts/, depend on ssccs-schemes, ssccs-examples, ssccs-primitive, ssccs-core)
```

## Rust Environment Setup

### 1. Install Rust

If you do not have Rust installed, use [rustup](https://rustup.rs/):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

Make sure the toolchain is up to date:

```bash
rustup update
```

### 2. Verify Installation

```bash
rustc --version
cargo --version
```

### 3. Clone the Repository

```bash
git clone https://github.com/ssccsorg/ssccs.git
cd ssccs/poc
```

## Building and Running

### Build the Project

```bash
cargo build --release --workspace
```

To build a specific crate, e.g., `cargo build --release -p ssccs-schemes`.

### Run Individual Experiments

Each constitutional concept test is a separate binary:

```bash
# Run all experiments
cargo run --bin concept-segment
cargo run --bin concept-field
cargo run --bin concept-projector
cargo run --bin concept-observation
cargo run --bin concept-space
cargo run --bin concept-scheme
cargo run --bin concept-adjacency
cargo run --bin concept-composite
cargo run --bin concept-transition
cargo run --bin concept-integrated

# Or run the integrated workflow (demonstrates complete pipeline)
cargo run --bin concept-integrated
```

### Run Unittests

```bash
cargo test --workspace -- --nocapture
```

To test only a specific crate, e.g., `cargo test -p ssccs-core`.

### Linting and Formatting

The code adheres to Rust's best practices. To check for warnings across the whole workspace:

```bash
cargo clippy --workspace -- -D warnings
```

To enforce consistent formatting across all crates:

```bash
cargo fmt --check --workspace
```

## Local CI Validation with Act

You can run the same CI workflow locally using [act](https://github.com/nektos/act), a tool that executes GitHub Actions workflows on your local machine.

### Prerequisites

1. Install `act`:

   ```bash
   # macOS (using Homebrew)
   brew install act

   # Linux (using the installation script)
   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
   ```

2. Ensure Docker is running.

### Running the Validation Job

To run the `rust-check` job defined in `.github/workflows/rust-poc-ci.yml`:

```bash
cd /path/to/ssccs/poc
act -j rust-check -P ubuntu-latest=catthehacker/ubuntu:act-latest
```

This will:

- Spin up a Docker container with the Ubuntu latest image
- Install the Rust toolchain, clippy, and rustfmt
- Cache dependencies
- Run the complete validation suite (`poc/run.sh`)

The validation script (`poc/run.sh`) performs the following checks in order:

1. **Formatting** – `cargo fmt --check`
2. **Linting** – `cargo clippy --workspace -- -D warnings`
3. **Build** – `cargo build --workspace --release`
4. **Tests** – `cargo test --workspace --all-targets --release`
5. **Binary execution** – Automatically discovers and runs all binary crates (the 10 constitutional concept tests)

If any step fails, the workflow stops and reports the error. A successful run ends with "ALL VALIDATIONS PASSED".

### Notes

- The first run will take longer due to Docker image downloads and dependency caching.
- Subsequent runs benefit from cached Docker layers and the Rust cache.
- The `catthehacker/ubuntu:act-latest` image is recommended for `act` because it includes common tools (including `jq`) that the validation script expects.

## Why Rust Was Chosen for the PoC

Rust was selected for several reasons:

1. **Memory Safety Without Garbage Collection** – SSCCS relies on precise control over memory layout and immutability guarantees that Rust's ownership system provides at compile time.

2. **Zero-Cost Abstractions** – The Scheme abstraction layer and Projector traits introduce no runtime overhead compared to hand-written code.

3. **Immutability by Default** – Segments and Schemes are immutable by design, aligning with Rust's emphasis on immutable data structures.

4. **Type System Expressiveness** – Rust's type system enables encoding SSCCS ontological distinctions (Segment vs. Scheme vs. Field) at the type level, preventing category errors at compile time.

5. **Cryptographic Primitives** – The BLAKE3 hashing library provides efficient cryptographic identity computation for Segments and Schemes.

## Architecture Overview

### ssccs-core

Contains absolute primitives that cannot be decomposed further:

- **`Coordinates`** – A vector of axis values representing a point in possibility space.
- **`Segment`** – An immutable wrapper around `Coordinates` with a BLAKE3-derived identity.
- **`SegmentId`** – Cryptographic identifier for a Segment.
- **`Constraint`** – Trait for dynamic constraints that can be attached to a Field.
- **`ConstraintSet`** – Collection of constraints indexed by name.
- **`Field`** – Mutable container holding constraints and transition matrices.
- **`TransitionMatrix`** – Weighted directed graph encoding relational topology between coordinates.
- **`Projector`** – Trait for semantic interpreters that observe Segment-Field pairs.
- **`observe`** – Function that performs observation by applying a Projector to a Segment-Field pair.
- **`possible_next_coordinates`** – Function that computes admissible next coordinates based on Field transitions.

### ssccs-primitive

Provides the Scheme abstraction layer:

- **`Scheme`** – Immutable structural blueprint containing axes, segments, relations, memory layout, and observation rules.
- **`SchemeBuilder`** – Builder pattern for constructing Schemes with fluent API.
- **`SchemeTrait`** – Trait defining the Scheme interface (id, axes, segments, validation, etc.).
- **`Axis`** – Definition of a structural dimension with name, type, and metadata.
- **`StructuralRelation`** – Enum for adjacency, hierarchy, dependency, and equivalence relations.
- **`MemoryLayout`** – Abstraction for mapping coordinates to logical addresses.
- **`ObservationRules`** – Configuration for observation behavior and conflict resolution.

### ssccs-schemes

Concrete Scheme implementations and developer input types:

- **`Grid2DTemplate`** – 2D grid Scheme with configurable topology (4-connected, 8-connected, toroidal).
- **`IntegerLineTemplate`** – 1D linear Scheme for integer arithmetic.
- **`GraphTemplate`** – Graph-based Scheme with arbitrary node-edge structure.
- **`Tensor3DTemplate`** – 3D tensor Scheme for multi-dimensional computation.
- **`CompositeScheme`** – Composition of multiple Schemes with combination rules.
- **`TransformedScheme`** – Geometric transformation (rotation, scaling, translation) applied to a base Scheme.
- **`BooleanSpace`** – Developer input type for boolean values.
- **`IntegerSpace`** – Developer input type for single-axis integer values.

### ssccs-examples

Shared utilities for experiments and examples:

- **`IntegerProjector`** – Extracts a coordinate along a given axis.
- **`ArithmeticProjector`** – Generates neighbors via arithmetic operations (+1, -1).
- **`ParityProjector`** – Classifies values as "even" or "odd".
- **`CoordinateSumProjector`** – Sums coordinates for 3D tensor observation.
- **`CompilerPipeline`** – Skeleton for compiling Schemes to hardware targets.
- **`HardwareProfile`** – Enum for CPU, FPGA, or PIM targets.
- **`.ss` Parser** – Binary format parser for Scheme serialization.
- **`RangeConstraint`** – Test constraint that checks if a value is within a range.
- **`EvenConstraint`** – Test constraint that checks if a value is even.

## Crate Responsibilities

### What Belongs in ssccs-core

Only absolute primitives that cannot be decomposed further:

- Core ontological types (Segment, Coordinates, Field, Constraint)
- The Projector trait (not implementations)
- Observation functions
- Transition matrix

### What Belongs in ssccs-primitive

Scheme abstraction layer:

- Scheme struct and builder
- SchemeTrait definition
- Structural relations and constraints
- Memory layout abstractions
- Observation rules

### What Belongs in ssccs-schemes

Concrete implementations and developer input:

- Scheme templates (Grid2D, IntegerLine, Graph, Tensor3D)
- Composite and Transformed Scheme extensions
- Spaces (BooleanSpace, IntegerSpace) as developer conveniences

### What Belongs in ssccs-examples

Shared utilities for experimentation:

- Projector implementations
- Compiler pipeline
- Parser implementations
- Test constraints

### What Belongs in Experiment Crates

Individual constitutional tests that:

- Demonstrate a specific SSCCS concept
- Can evolve independently
- May be refactored or replaced as the model evolves

## License

This project is licensed under the same terms as the main SSCCS repository.

## Contributing

See the main repository's [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.
