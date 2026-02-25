# SSCCS Proof of Concept (PoC)

This repository contains a proof‑of‑concept implementation of the **Schema–Segment Composition Computing System (SSCCS)**, a new computational model that redefines computation as the observation of structured potential rather than as a sequence of state mutations.

The PoC demonstrates the core ontological layers of SSCCS:
- **Segment** – immutable coordinate points in a multi‑dimensional possibility space.
- **Scheme** – immutable structural blueprint defining axes, segments, relations, memory layout, and observation rules.
- **Field** – mutable container of dynamic constraints.
- **Projector** – semantic interpreter that observes a combination of Field and Segment to produce a projection.
- **Observation** – the sole active event that collapses admissible configurations into a deterministic projection.

The implementation is written in Rust and serves as a reference for the software‑emulation phase (Phase 1) of the SSCCS roadmap.

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
cargo build --release
```

### Run the Example Program
The PoC includes ten constitutional‑concept tests that validate the SSCCS model:

```bash
cargo run --release
```

This executes the `main` function, which runs the same ten tests and prints a summary.

#### Run Unittests

```bash
cargo test -- --nocapture
```

The output will show each test (Segment, Field, Projector, Scheme, etc.) passing.


### Linting and Formatting
The code adheres to Rust’s best practices. To check for warnings:

```bash
cargo clippy -- -D warnings
```

To enforce consistent formatting:

```bash
cargo fmt --check
```

## Why Rust Was Chosen for the PoC

Rust’s design philosophy aligns closely with the SSCCS model, making it the natural language for this proof of concept.

### 1. Immutability by Default
SSCCS requires that Segments and Schemes be **immutable**. Rust’s ownership system enforces immutability unless explicit mutability is declared (`mut`). This guarantees that the core SSCCS structures cannot be accidentally mutated, matching the ontological requirement that “structure is fixed.”

### 2. Zero‑Cost Abstractions
SSCCS aims to turn structural specification into efficient hardware mapping. Rust’s zero‑cost abstractions allow high‑level descriptions (e.g., `RelationGraph`, `MemoryLayout`) to compile to machine code with no runtime overhead, preserving the performance needed for future hardware acceleration.

### 3. Concurrency Without Data Races
Because Segments are immutable, they can be observed concurrently without synchronization. Rust’s borrow checker statically guarantees that immutable references can be shared freely across threads, while mutable references are exclusive. This eliminates data races **at compile time**, which is exactly the concurrency model SSCCS intends to exploit.

### 4. Cryptographic Primitives and Performance
Segment and Scheme identities are derived from BLAKE3 hashes. Rust’s `blake3` crate provides fast, safe, and well‑audited cryptographic hashing, enabling the verifiable identity system that underpins SSCCS’s auditability.

### 5. Strong Type System for Structural Invariants
The Scheme abstraction layer uses Rust’s enum and trait system to encode **axis types**, **relation types**, **layout types**, and **observation rules** as compile‑time types. This ensures that invalid structural configurations cannot be represented, catching many logical errors before runtime.

### 6. Ecosystem for Systems Programming
As a systems language, Rust gives fine‑grained control over memory layout (via `#[repr(C)]`, packed structs, etc.), which is essential for implementing the `MemoryLayout` mapping that translates coordinate spaces to hardware addresses.

### 7. Safety and Auditability
SSCCS emphasizes transparency and verifiability. Rust’s memory‑safety guarantees (no undefined behavior, no use‑after‑free, no buffer overflows) reduce the risk of hidden bugs that could compromise the deterministic observation process. This aligns with the SSCCS goal of “computation as auditable trace.”

In summary, Rust provides the right combination of **immutability guarantees**, **performance control**, **concurrency safety**, and **cryptographic support** to faithfully prototype the SSCCS model while laying a foundation for future hardware‑acceleration phases.

## Detailed Work Log

The following development milestones have been completed, each documented in the `docs/` directory and reflected in the codebase.

### 1. Core Library (`src/core.rs`)
- **Segment** struct with coordinates and cryptographic `SegmentId` (BLAKE3 hash).
- **SpaceCoordinates** as a generic multi‑dimensional coordinate vector.
- **Constraint** trait and `ConstraintSet` for defining admissibility conditions.
- **Field** struct that holds constraints and a `TransitionMatrix` for relational topology.
- **Projector** trait with `project` and `possible_next_coordinates` methods.

### 2. Scheme Abstraction Layer (`src/scheme/`)
- **`abstract_scheme.rs`** (970 lines) – defines `Scheme`, `Axis`, `RelationGraph`, `MemoryLayout`, `ObservationContext`, and `SchemeBuilder`.
  - Type aliases `PredicateFn` and `MappingFn` for complex closure types.
  - Comprehensive enumeration of structural relations (`Adjacency`, `Hierarchy`, `Dependency`, `Equivalence`).
  - Memory‑layout types (`Linear`, `RowMajor`, `ColumnMajor`, `SpaceFillingCurve`, etc.).
  - Ready‑to‑use templates: `Grid2DTemplate`, `IntegerLineTemplate`, `GraphTemplate`.
- **`mod.rs`** (437 lines) – defines `SchemeImpl` enum (`Basic`, `Composite`, `Transformed`) and the `SchemeTrait` with methods for identity, axes, segments, validation, and logical‑address mapping.
  - `CompositeScheme` with composition rules and conflict resolution.
  - `TransformedScheme` with geometric transformations (translation, rotation, scaling).

### 3. Compiler Pipeline (`src/compiler_pipeline.rs`)
- Four‑stage pipeline: parsing, structural analysis, memory‑layout resolution, hardware mapping.
- `HardwareProfile` enum (`GenericCPU`, `FPGA`, `PIM`, `Custom`).
- `CompiledScheme` struct that holds the final hardware‑mapped layout and generated observation code.
- Placeholder implementations for each stage, ready for extension.

### 4. `.ss` Binary Parser (`src/ss_parser.rs`)
- Basic parser for the open `.ss` binary format.
- Validates header magic and version.
- Reads SchemeId, axes, segment table, relation graph, memory‑layout closure, and observation rules.
- Returns a dummy `Scheme` for demonstration; serves as a skeleton for future elaboration.

### 5. Projector Implementations (`src/projector.rs`)
- `IntegerProjector` – extracts a coordinate along a given axis.
- `ArithmeticProjector` – defines adjacency through arithmetic operations (`+1`, `-1`, `*2`, `/2`).
- `ParityProjector` – classifies coordinates as “even” or “odd” strings.

### 6. Constitutional Concept Tests (`src/main.rs`)
Ten tests verify that the SSCCS model satisfies its foundational principles:

1. **Segment Concept** – immutability and cryptographic identity.
2. **Field Concept** – constraint admissibility and transition topology.
3. **Projector Concept** – semantic interpretation of Segment‑Field pairs.
4. **Observation Concept** – deterministic projection via `observe` function.
5. **Space Concept** – coordinate dimensionality and axis access.
6. **Scheme Concept** – structural blueprint with Grid2D and IntegerLine templates.
7. **Adjacency Memory** – memory‑layout mapping for a 2D grid.
8. **Composite and Transformed Schemes** – composition and geometric transformation.
9. **Transition Matrix** – weighted directed‑graph relationships.
10. **Integrated Workflow** – end‑to‑end observation of a simple computational scenario.

All ten tests pass, confirming that the PoC correctly embodies the SSCCS ontology.

### 7. Code Quality and Maintenance
- **Clippy linting** – resolved 10 warnings (type‑complexity, unnecessary‑map‑or, large‑enum‑variant, needless‑borrow, clone‑on‑copy) by introducing type aliases, boxing large variants, and removing redundant operations.
- **Formatting** – module order adjusted to satisfy `cargo fmt`.
- **Documentation** – inline doc comments and references to the whitepaper.

### 8. Whitepaper Synchronization
The implementation stays aligned with the conceptual description in `docs/Whitepaper.qmd`:
- Ontological layers (Segment, Scheme, Field, Observation, Projection) match the code.
- Compiler‑pipeline section (Section 5.1) corresponds to `compiler_pipeline.rs`.
- Memory‑layout abstraction (Section 5.2) is realized as `MemoryLayout` in `abstract_scheme.rs`.
- Open `.ss` format (Section 6) is stubbed in `ss_parser.rs`.

### 9. Next Steps (Immediate)
- Extend the `.ss` parser to fully deserialize a Scheme.
- Implement the hardware‑mapping stage with concrete cache‑line and bank‑interleaving logic.
- Add more realistic projectors (e.g., floating‑point operations, image‑pixel interpretation).
- Benchmark data‑movement reduction against a traditional vector‑addition loop.

## License

This PoC is released under the **Apache License 2.0**. See the [LICENSE](../LICENSE) file for details.

The accompanying whitepaper (`docs/Whitepaper.qmd`) is licensed under **CC BY‑NC‑ND 4.0**.

## Acknowledgments

SSCCS is a non‑profit research initiative (SSCCS gUG i.G.). The PoC was developed as a reference implementation to validate the model’s feasibility and to invite collaboration from the open‑source and research communities.

For more information, visit the [SSCCS GitHub organization](https://github.com/ssccsorg/ssccs) or read the full whitepaper in `docs/Whitepaper.pdf`.