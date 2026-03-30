# PoC Diagnosis and Roadmap

## Context

This issue defines the strategic direction for the SSCCS Proof-of-Concept (PoC) development, drawing from the following documents:

- **Whitepaper Appendix** (`docs/whitepaper/_include/_appendix.qmd`) – provides detailed implementation notes, open‑format specification, hardware‑profile variants, and concrete examples (vector addition, N‑dimensional tensors, graph processing).
- **Main Whitepaper** (`docs/whitepaper/whitepaper.qmd`) – articulates the core SSCCS ontology (Segment, Scheme, Field, Observation, Projection) and the compiler pipeline.
- **Diagnosis Report** (`docs/report/diagnosis.qmd`) – offers a rigorous gap assessment and a three‑track implementation roadmap (Field Synthesis, Hardware Mapping, Compiler Optimisations).
- **Current PoC Workspace** (`poc/`) – the Rust‑based reference implementation that validates the core concepts.

The goal is to translate the theoretical and strategic insights into actionable development tasks that will elevate the PoC from TRL 3‑4 (experimental proof of concept) to TRL 5‑6 (prototype demonstration in a relevant environment).

## Current PoC State (as of 2026‑03‑30)

### What’s Implemented

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
   - **New**: `Tensor3DTemplate` – 3D tensor with 6‑connected Manhattan adjacency (added as a complex multi‑dimensional example).

4. **Projector Extensions** (`projector.rs`):
   - `CoordinateSumProjector` – sums the three coordinate values of a segment (used with the 3D tensor example).

5. **Constitutional Tests** (`main.rs`):
   - Ten tests that validate the core concepts (segment, field, projector, observation, scheme, adjacency memory, composite/transformed schemes, transition matrix, integrated workflow).
   - The integrated‑workflow test now uses the `Tensor3DTemplate` and `CoordinateSumProjector`, demonstrating a complete observation cycle.

6. **Compiler‑Pipeline Skeleton** (`compiler_pipeline.rs`):
   - Placeholder for the four‑stage pipeline (parsing, structural analysis, memory‑layout resolution, hardware mapping).

7. **`.ss` Parser Stub** (`ss_parser.rs`):
   - Basic structure for reading the open‑format binary (currently a dummy implementation).

8. **Boolean and Integer Spaces** (`spaces/boolean.ss`, `integer.ss`):
   - Example `.ss` files (currently Rust macro code) that illustrate the concept of a space definition.

### What’s Missing (Technical Gaps)

1. **Field Composition Algebra** – no implementation of union, intersection, or product operators for Fields. The algebraic formalisation described in the whitepaper (Section 3.3) is not yet realised in code.
2. **Hardware‑Mapping Concrete Implementation** – the compiler pipeline lacks real mapping to CPU caches, FPGA Block‑RAM, HBM, or PIM substrates. The memory‑layout abstraction is defined but not yet lowered to physical addresses.
3. **Observation‑Code Generation** – no code generation for CPU SIMD loops, FPGA Verilog netlists, or PIM commands. The observation‑code generation methodology (Appendix A.5) is only described on paper.
4. **Open‑Format Specification Finalization** – the `.ss` binary format is only a stub; the full specification (Appendix A.4) is not yet implemented.
5. **Formal Verification** – no mechanized proofs of determinism or race‑freedom.
6. **Benchmarking Suite** – no systematic performance/energy comparisons against baseline architectures (RISC‑V, GPU, PIM).

## Technical Challenges and Insights

### Structural Superiority and Extensibility

The recent addition of the `Tensor3DTemplate` illustrates SSCCS’s **structural superiority**: a new scheme template can be added without modifying the existing field, projector, or observation mechanisms. This modularity follows the same pattern as the existing templates (`Grid2DTemplate`, `IntegerLineTemplate`, `GraphTemplate`) and demonstrates that the system is **extensible by construction**. The insight is that the Scheme abstraction layer serves as a **plugin architecture** for topological patterns; any new domain‑specific topology can be encapsulated as a template, reusing the entire downstream stack.

### Mapping Structural Relations to Hardware

A core challenge is translating the high‑level structural relations (adjacency, hierarchy, dependency) into hardware‑specific layouts that preserve locality. The whitepaper proposes an **Observation Intermediate Representation (OIR)** that captures Segments as nodes and constraints as edges, which can then be synthesised directly into FPGA interconnect or PIM command sequences. The key insight is that **structural adjacency can be hardwired**; for example, a 2D grid with Manhattan adjacency can be mapped to a row‑major memory layout where neighbouring Segments reside in adjacent cache lines, eliminating pointer‑chasing overhead.

### Deterministic Observation and Race‑Freedom

Because Segments are immutable and Fields are the only mutable layer, concurrent observations on disjoint Segments are trivially race‑free. This property can be formally proved and leveraged to design hardware that performs **parallel observation without locks**. The challenge is to ensure that the observation operator `Ω` is deterministic even when multiple admissible configurations exist; the whitepaper’s observation rules (resolution strategies) must be implemented in a way that guarantees repeatability across runs.

### Field Composition Algebra

Fields are meant to be composed via union, intersection, and product operators. The algebraic laws of these operators (e.g., idempotence, commutativity, distributivity) need to be verified, and the composition must preserve observation determinism. Implementing these operators efficiently requires careful representation of constraints—possibly as Boolean formulas or symbolic predicates—and integration with the transition‑matrix arithmetic.

### Energy‑Efficiency Projections

The whitepaper’s energy model predicts that SSCCS can reduce energy consumption by eliminating data movement. However, this prediction must be validated with actual measurements. The **energy per observation** depends on the hardware substrate: on an FPGA, observation could be combinatorial with near‑zero dynamic power; on a CPU, it will involve SIMD loads and arithmetic. A benchmarking suite must be built to quantify the energy advantage for representative kernels (vector addition, 2D convolution, graph BFS).

## Proposed Development Roadmap (Phased)

### Phase 1: Foundation (Next 3–6 Months)

**Goal**: Implement the missing core components and establish a baseline benchmarking suite.

1. **Field Composition** (`field‑synthesis` crate):
   - Implement `Field::union`, `Field::intersection`, `Field::product` methods.
   - Define algebraic properties as unit tests (e.g., `union` is commutative, `intersection` distributes over `union`).
   - Integrate with the existing `Field` struct and update the observation logic to respect composed constraints.

2. **Open‑Format Parser** (`primitive` crate):
   - Read a real `.ss` binary (e.g., the Boolean space) and produce a `Scheme` instance.
   - Validate against the open‑format specification (Appendix A.4).
   - Extend the parser to handle all axis types, relation categories, and memory‑layout variants.

3. **Compiler Pipeline – Structural Analysis** (`compiler‑opt` crate):
   - Extract adjacency and dependency relations from a parsed Scheme.
   - Identify independent sub‑graphs (strongly connected components) for parallel observation.
   - Output a partition of the Scheme into observation units.

4. **Compiler Pipeline – Memory‑Layout Resolution** (`compiler‑opt` crate):
   - Implement the mapping functions for row‑major, column‑major, space‑filling‑curve, hierarchical, and graph‑based layouts.
   - Generate a logical‑address map for each observation unit.
   - Verify that structurally adjacent Segments receive proximate logical addresses.

5. **Benchmarking Suite** (new crate `benchmarks`):
   - Define three kernels: vector addition (memory‑bound), 2D convolution (compute‑bound), graph BFS (irregular).
   - Implement each kernel in pure Rust (baseline) and as an SSCCS Scheme + Field + Projector.
   - Measure execution time and (where possible) energy using hardware performance counters (e.g., `perf` on Linux, `rdpmc`).
   - Compare SSCCS emulation against the baseline; document any overheads.

### Phase 2: Hardware Mapping (Next 6–12 Months)

**Goal**: Lower the SSCCS representation to concrete hardware backends and measure real energy savings.

1. **Hardware‑Profile Expansion** (`hardware‑mapping` crate):
   - Define profiles for CPU (cache‑line alignment, SIMD width), FPGA (Block‑RAM, LUT count), PIM (bank‑level parallelism).
   - Extend the compiler pipeline to accept a profile and adjust the logical‑address map accordingly.

2. **Observation‑Code Generation – CPU** (`compiler‑opt` crate):
   - Lower a simple Scheme (integer line) to LLVM IR via a custom MLIR dialect (or directly via `inkwell`).
   - Generate x86‑64/RISC‑V machine code that implements the observation operator as a SIMD loop.
   - Integrate with the benchmarking suite to compare against the Rust emulation.

3. **Observation‑Code Generation – FPGA** (`hardware‑mapping` crate):
   - Develop a Verilog backend that translates the OIR into a combinatorial or pipelined data‑path.
   - Synthesise the Verilog for a low‑cost FPGA (e.g., Arty A7) using Yosys/nextpnr.
   - Measure power consumption with on‑board monitors (INA260) and compare against a soft‑core RISC‑V running the same kernel.

4. **Observation‑Code Generation – PIM** (`hardware‑mapping` crate):
   - Create a stub backend that emits PIM command sequences (following the hypothetical SDK described in Appendix A.5).
   - Simulate the commands in a software model to verify correctness.

5. **Formal Verification** (separate Lean/Coq project):
   - Mechanise the determinism proof for a single observation on a single Field.
   - Prove commutativity of concurrent observations on non‑overlapping Segments.
   - Integrate the proofs into the CI pipeline (e.g., via `lean‑checker`).

### Phase 3: Integration and Scaling (12–24 Months)

**Goal**: Combine the three tracks into a unified, scalable SSCCS stack and demonstrate end‑to‑end applications.

1. **Integrated Compiler**:
   - Merge the field‑synthesis, hardware‑mapping, and compiler‑opt crates into a single `ssccs‑compiler` binary.
   - Support command‑line flags for target profile, optimisation level, and output format (executable, Verilog, PIM commands).

2. **Domain‑Specific Demonstrators**:
   - Implement a complete SSCCS‑based **image‑processing pipeline** (2D convolution, pooling, reshaping) and compare against OpenCV.
   - Implement a **graph neural‑network layer** using the GraphTemplate and a custom projector that aggregates neighbour features.
   - Implement a **finite‑element‑method kernel** that exploits the tensor template for sparse matrix‑vector multiplication.

3. **Performance and Energy Validation**:
   - Run the demonstrators on the FPGA prototype and collect comprehensive energy measurements.
   - Publish a peer‑reviewed paper with quantified advantages (energy reduction, determinism guarantees, scalability).

4. **Tooling and Ecosystem**:
   - Create a VS‑Code extension for `.ss` files (syntax highlighting, schema validation).
   - Develop a graphical visualiser for Schemes and Fields (using `egui` or `iced`).
   - Write comprehensive user and developer documentation.

## Immediate Next Actions (Next 4 Weeks)

1. **Implement Field composition operators** – assign to a developer familiar with Rust and algebraic structures.
2. **Extend the `.ss` parser** – parse the Boolean space binary and integrate with the existing Scheme builder.
3. **Start the benchmarking suite** – set up `criterion` for the three kernels and collect baseline measurements.
4. **Design the OIR data structure** – draft the Observation Intermediate Representation and its serialisation format.
5. **Begin formal verification** – define the semantics of a single observation in Lean/Coq and prove determinism for a trivial case.

## Conclusion

This roadmap focuses exclusively on the technical evolution of the PoC, stripping away organisational and global‑collaboration concerns. The path forward is clear: complete the core algebra (Field composition), realise the compiler pipeline (structural analysis, memory‑layout resolution, hardware mapping), generate observation code for multiple targets, and validate the energy‑efficiency claims through rigorous benchmarking. 

---

*References*:

- Whitepaper Appendix: [`docs/whitepaper/_include/_appendix.qmd`](docs/whitepaper/_include/_appendix.qmd)
- Main Whitepaper: [`docs/whitepaper/whitepaper.qmd`](docs/whitepaper/whitepaper.qmd)
- Diagnosis Report: [`docs/report/diagnosis.qmd`](docs/report/diagnosis.qmd)
- PoC Workspace: [`poc/`](poc/)