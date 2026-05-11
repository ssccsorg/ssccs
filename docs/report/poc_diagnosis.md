# PoC Diagnosis and Roadmap

2026-05-11

SSCCS Foundation

## Context

This issue defines the strategic direction for the SSCCS Proof-of-Concept (PoC) development, drawing from the following documents:

- **Whitepaper Appendix** (`/docs/whitepaper/_include/_appendix.qmd`) – provides detailed implementation notes, open‑format specification, hardware‑profile variants, and concrete examples (vector addition, N‑dimensional tensors, graph processing).
- **Main Whitepaper** (`/docs/whitepaper/whitepaper.qmd`) – articulates the core SSCCS ontology (Segment, Scheme, Field, Observation, Projection) and the compiler pipeline.
- **Diagnosis Report** (`/docs/report/poc_diagnosis.qmd`) – offers a rigorous gap assessment and a three‑track implementation roadmap (Field Synthesis, Hardware Mapping, Compiler Optimisations).
- **Current PoC Workspace** (`/poc/`) – the Rust‑based reference implementation that validates the core concepts.

The goal is to translate the theoretical and strategic insights into actionable development tasks that will elevate the PoC from experimental validation toward prototype demonstration in a relevant environment. The architectural evolution will be supported by a parallel knowledge-publishing and AI-context sub-project that ensures all theoretical artifacts, implementation notes, and benchmark results are structured, cross-referenced, and machine-readable.

## Current PoC State

### What's Implemented

1. **Core Types** (`ssccs‑core`):
   - `Segment` with cryptographic identity (BLAKE3 hash) and immutable coordinates.
   - `SpaceCoordinates` representing multi‑dimensional positions.
   - `Field` holding dynamic constraints and a `TransitionMatrix`.
   - `Projector` trait with three example projectors (`IntegerProjector`, `ArithmeticProjector`, `ParityProjector`).
   - Observation functions that collapse a Scheme‑Field pair into a projection.

2. **Scheme Abstraction Layer** (`ssccs‑primitive/src/scheme/`):
   - Axis types (`Discrete`, `Continuous`, `Cyclic`, `Categorical`, `Relational`, `WithUnit`).
   - Structural‑relation categories (`Adjacency`, `Hierarchy`, `Dependency`, `Equivalence`, `Custom`).
   - Memory‑layout taxonomy (`Linear`, `RowMajor`, `ColumnMajor`, `SpaceFillingCurve`, `Hierarchical`, `Graph‑Based`, `Custom`).
   - Observation‑rule definitions (resolution strategies, triggers, priority, context).

3. **Pre‑defined Scheme Templates** (`abstract_scheme.rs`):
   - `Grid2DTemplate` – regular 2D lattice with configurable topology.
   - `IntegerLineTemplate` – one‑dimensional discrete line.
   - `GraphTemplate` – arbitrary graph connectivity.
   - `Tensor3DTemplate` – 3D tensor with 6‑connected Manhattan adjacency.

4. **Projector Extensions** (`projector.rs`):
   - `CoordinateSumProjector` – sums the three coordinate values of a segment.

5. **Constitutional Tests** (`main.rs`):
   - Fourteen tests validating core concepts including segment, field, projector, observation, scheme, adjacency memory, composite/transformed schemes, transition matrix, and integrated workflow.
   - Integrated‑workflow test uses `Tensor3DTemplate` and `CoordinateSumProjector` to demonstrate a complete observation cycle.

6. **Compiler‑Pipeline Skeleton** (`compiler_pipeline.rs`):
   - Placeholder for the four‑stage pipeline (parsing, structural analysis, memory‑layout resolution, hardware mapping).

7. **`.ss` Parser Stub** (`ss_parser.rs`):
   - Basic structure for reading the open‑format binary.

8. **Boolean and Integer Spaces** (`spaces/boolean.ss`, `integer.ss`):
   - Example `.ss` files illustrating space definition concepts.

9. **Field Composition Algebra** (`field‑synthesis` crate):
   - `ComposedField` implementing union (`∪`), intersection (`∩`), and product (`×`) operators.
   - Twelve algebraic law tests: commutativity, associativity, distributivity, absorption, identity, idempotence.
   - `compose_observe()` bridge connecting composed constraints to projectors.
   - Transition matrix composition via `transition_targets()`.

10. **Scenario Framework** (`scenarios/` module):
    - `Scenario` trait with auto‑registration and discovery.
    - `Grid2D` scenario: parity constraint × range constraint over 9 segments.
    - `Sensor×Time×Temperature` scenario: heterogeneous axes demonstrating independent semantics per dimension.

11. **RISC‑V Assembly Engine** (`baremetal_riscv/`):
    - `observe_full.S`: 350+ line observation pipeline with branchless constraints, weighted composition, batch observation.
    - Pure‑Rust fallback with golden‑anchor verification for CI validation on x86_64.
    - `build.rs` auto‑generates `asm_data.rs` from `.S` data directives, ensuring compile‑time drift detection.
    - `global_asm!` integration with `#[cfg(target_arch = "riscv64")]` guards.

12. **CI Validation Pipeline**:
    - `run.sh --validation` executes fmt → clippy → build → test → binary‑crate discovery.
    - `act` local testing confirms workflow compatibility.
    - Golden‑anchor tests parse expected results directly from `.S` comments, enforcing synchronization between assembly and Rust fallback.

### What's Missing (Technical Gaps)

1. **Open‑Format Parser Completion** – the `.ss` binary format remains a stub; full specification (Appendix A.4) requires implementation.
2. **Hardware‑Mapping Concrete Implementation** – compiler pipeline lacks real mapping to CPU caches, FPGA Block‑RAM, HBM, or PIM substrates.
3. **Observation‑Code Generation** – no code generation for CPU SIMD loops, FPGA Verilog netlists, or PIM commands.
4. **Formal Verification** – no mechanized proofs of determinism or race‑freedom.
5. **Benchmarking Suite** – no systematic performance/energy comparisons against baseline architectures (RISC‑V, GPU, PIM).
6. **Rust‑to‑Assembly Bridge** – Rust `ComposedField` and `Scheme` definitions do not yet generate assembly data or observe function chains automatically.

## Technical Challenges and Insights

### Structural Superiority and Extensibility

The `Tensor3DTemplate` and `Sensor×Time×Temperature` scenario demonstrate SSCCS structural superiority: new scheme templates integrate without modifying existing field, projector, or observation mechanisms. The Scheme abstraction layer functions as a plugin architecture for topological patterns; domain‑specific topologies encapsulate as templates, reusing the entire downstream stack.

### Mapping Structural Relations to Hardware

Translating high‑level structural relations (adjacency, hierarchy, dependency) into hardware‑specific layouts that preserve locality remains a core challenge. The whitepaper proposes an Observation Intermediate Representation (OIR) capturing Segments as nodes and constraints as edges, synthesizable directly into FPGA interconnect or PIM command sequences. Structural adjacency can be hardwired: a 2D grid with Manhattan adjacency maps to row‑major memory layout where neighbouring Segments reside in adjacent cache lines, eliminating pointer‑chasing overhead.

### Deterministic Observation and Race‑Freedom

Segments are immutable and Fields constitute the only mutable layer, making concurrent observations on disjoint Segments trivially race‑free. This property supports hardware designs performing parallel observation without locks. Ensuring the observation operator `Ω` remains deterministic across multiple admissible configurations requires implementing whitepaper observation rules (resolution strategies) with repeatability guarantees.

### Field Composition Algebra

Fields compose via union, intersection, and product operators. Algebraic laws (idempotence, commutativity, distributivity) require verification, and composition must preserve observation determinism. Efficient implementation demands careful constraint representation—possibly as Boolean formulas or symbolic predicates—integrated with transition‑matrix arithmetic.

### Energy‑Efficiency Projections

The whitepaper energy model predicts SSCCS reduces energy consumption by eliminating data movement. Validation requires actual measurements. Energy per observation depends on hardware substrate: FPGA observation could be combinatorial with near‑zero dynamic power; CPU observation involves SIMD loads and arithmetic. A benchmarking suite must quantify energy advantages for representative kernels (vector addition, 2D convolution, graph BFS).

## Proposed Development Roadmap (Phased)

### Phase 1: Foundation

**Goal**: Implement missing core components and establish a baseline benchmarking suite.

1. **Open‑Format Parser** (`primitive` crate):
   - Parse a real `.ss` binary (e.g., Boolean space) into a `Scheme` instance.
   - Validate against open‑format specification (Appendix A.4).
   - Extend parser to handle all axis types, relation categories, and memory‑layout variants.

2. **Compiler Pipeline – Structural Analysis** (`compiler‑opt` crate):
   - Extract adjacency and dependency relations from parsed Scheme.
   - Identify independent sub‑graphs (strongly connected components) for parallel observation.
   - Output partition of Scheme into observation units.

3. **Compiler Pipeline – Memory‑Layout Resolution** (`compiler‑opt` crate):
   - Implement mapping functions for row‑major, column‑major, space‑filling‑curve, hierarchical, and graph‑based layouts.
   - Generate logical‑address map for each observation unit.
   - Verify structurally adjacent Segments receive proximate logical addresses.

4. **Benchmarking Suite** (new crate `benchmarks`):
   - Define three kernels: vector addition (memory‑bound), 2D convolution (compute‑bound), graph BFS (irregular).
   - Implement each kernel in pure Rust (baseline) and as SSCCS Scheme + Field + Projector.
   - Measure execution time and energy using hardware performance counters.
   - Compare SSCCS emulation against baseline; document overheads.

### Phase 2: Hardware Mapping

**Goal**: Lower SSCCS representation to concrete hardware backends and measure real energy savings.

1. **Hardware‑Profile Expansion** (`hardware‑mapping` crate):
   - Define profiles for CPU (cache‑line alignment, SIMD width), FPGA (Block‑RAM, LUT count), PIM (bank‑level parallelism).
   - Extend compiler pipeline to accept profile and adjust logical‑address map accordingly.

2. **Observation‑Code Generation – CPU** (`compiler‑opt` crate):
   - Lower simple Scheme (integer line) to LLVM IR via custom MLIR dialect or `inkwell`.
   - Generate x86‑64/RISC‑V machine code implementing observation operator as SIMD loop.
   - Integrate with benchmarking suite to compare against Rust emulation.

3. **Observation‑Code Generation – FPGA** (`hardware‑mapping` crate):
   - Develop Verilog backend translating OIR into combinatorial or pipelined data‑path.
   - Synthesize Verilog for low‑cost FPGA using Yosys/nextpnr.
   - Measure power consumption with on‑board monitors; compare against soft‑core RISC‑V running same kernel.

4. **Observation‑Code Generation – PIM** (`hardware‑mapping` crate):
   - Create stub backend emitting PIM command sequences (following hypothetical SDK in Appendix A.5).
   - Simulate commands in software model to verify correctness.

5. **Formal Verification** (separate Lean/Coq project):
   - Mechanize determinism proof for single observation on single Field.
   - Prove commutativity of concurrent observations on non‑overlapping Segments.
   - Integrate proofs into CI pipeline.

### Phase 3: Integration and Scaling

**Goal**: Combine three tracks into unified, scalable SSCCS stack and demonstrate end‑to‑end applications.

1. **Integrated Compiler**:
   - Merge field‑synthesis, hardware‑mapping, and compiler‑opt crates into single `ssccs‑compiler` binary.
   - Support command‑line flags for target profile, optimisation level, and output format (executable, Verilog, PIM commands).

2. **Domain‑Specific Demonstrators**:
   - Implement complete SSCCS‑based image‑processing pipeline (2D convolution, pooling, reshaping) and compare against OpenCV.
   - Implement graph neural‑network layer using GraphTemplate and custom projector aggregating neighbour features.
   - Implement finite‑element‑method kernel exploiting tensor template for sparse matrix‑vector multiplication.

3. **Performance and Energy Validation**:
   - Run demonstrators on FPGA prototype; collect comprehensive energy measurements.
   - Publish peer‑reviewed paper with quantified advantages (energy reduction, determinism guarantees, scalability).

4. **Tooling and Ecosystem**:
   - Create VS‑Code extension for `.ss` files (syntax highlighting, schema validation).
   - Develop graphical visualiser for Schemes and Fields.
   - Write comprehensive user and developer documentation.

## Sub-Project: RISC-V Hardware Integration

A parallel research track investigates Rust bare-metal programming for RISC-V targets as a foundation for SSCCS hardware integration. See [`docs/research/rust_baremetal.qmd`](https://github.com/ssccsorg/ssccs/blob/main/docs/research/rust_baremetal.qmd) for details on leveraging the Rust embedded ecosystem to accelerate SSCCS validation on OpenHW CORE-V and other RISC-V platforms.

## Immediate Next Actions

1. **Extend the `.ss` parser** – parse the Boolean space binary and integrate with the existing Scheme builder.
2. **Design the OIR data structure** – draft the Observation Intermediate Representation and its serialisation format.
3. **Begin formal verification** – define the semantics of a single observation in Lean/Coq and prove determinism for a trivial case.
4. **Build Rust‑to‑Assembly bridge** – enable `build.rs` to generate assembly data sections and observe function chains from Rust `Scheme` + `ComposedField` definitions.
5. **Set up benchmarking infrastructure** – configure `criterion` for the three kernels and collect baseline measurements.

## Conclusion

This roadmap focuses exclusively on the technical evolution of the PoC. The path forward is clear: complete the compiler pipeline (structural analysis, memory‑layout resolution, hardware mapping), generate observation code for multiple targets, and validate energy‑efficiency claims through rigorous benchmarking. A parallel RISC‑V hardware‑integration sub‑project investigates Rust bare‑metal programming as a foundation for SSCCS validation on open RISC‑V platforms. The Field Composition Algebra and Scenario Framework now provide a solid foundation for advancing to hardware‑mapping and code‑generation phases.
