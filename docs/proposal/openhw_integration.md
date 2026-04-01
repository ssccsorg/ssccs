# SSCCS Validation with OpenHW CORE-V Ecosystem

**Date:** April 2026  
**From:** SSCCS Foundation


## Executive Summary

SSCCS (Schema–Segment Composition Computing System) is an open-source research initiative developing a new computational paradigm based on structural observation rather than instruction sequencing. This proposal outlines a technical collaboration with OpenHW Group to:

1.  Demonstrate SSCCS on OpenHW's **CORE-V processor family** using the **CORE-V eXtension Interface (XIF)**.
2.  Validate the performance and energy efficiency claims of the SSCCS model on real silicon (CV32E40P core and CORE-V MCU DevKit).
3.  Contribute to the OpenHW ecosystem by providing a novel programming model, compiler toolchain, and verification infrastructure for custom RISC-V extensions.

This collaboration aligns with OpenHW's mission to provide high-quality, open-source processor IP and to foster innovation in IoT, AI, and embedded systems.

**Why OpenHW?** The CORE-V ecosystem uniquely combines (1) open-source RISC-V IP, (2) flexible XIF extension interface, and (3) eFPGA-enabled prototyping—all essential for validating a new computational paradigm like SSCCS. Proprietary cores cannot offer the transparency required for structural observation research; SSCCS cannot offer real-silicon validation without OpenHW's accessible hardware stack. This collaboration is mutually enabling.


## Technical Alignment: SSCCS and OpenHW CORE-V

| Feature | OpenHW CORE-V | SSCCS Value Add |
|---------|---------------|-----------------|
| **Custom Instruction Support** | CORE-V XIF enables tightly coupled coprocessors without modifying core RTL. | SSCCS can implement **observation instructions** as custom XIF coprocessor extensions. |
| **Open-Source Verification** | CORE-V-VERIF testbench uses RVVI methodology and Imperas reference models. | SSCCS provides a **verifiable execution model** – observation results are deterministic by design, simplifying verification. |
| **Hardware Platform** | CORE-V MCU DevKit (CV32E40P core + Quicklogic eFPGA). | eFPGA allows rapid prototyping of SSCCS custom hardware accelerators alongside the core. |
| **Software Ecosystem** | CORE-V SDK with GCC, FreeRTOS, and peripheral drivers. | SSCCS compiler can target the SDK, enabling seamless integration of SSCCS-optimized libraries into existing software stacks. |
| **Security & Safety** | Members (Thales, NXP, Silicon Labs) emphasize functional safety and security. | SSCCS deterministic dataflow prevents speculative execution leaks and memory corruption by design. |


### Synergies with CORE‑V Vector and Security Extensions

Beyond the XIF interface, SSCCS can leverage other OpenHW CORE‑V features to amplify its benefits:

- **Vector Extensions (RVV) [14]**: The observation of regular Schemes (e.g., grids, tensors) can be mapped to vector instructions, allowing a single observation primitive to project an entire row or column of Segments in parallel. This synergy turns SSCCS’s structural parallelism into hardware‑accelerated vector throughput, providing a natural migration path from scalar custom instructions to vectorised observation.

- **Security Extensions (e.g., ePMP, Crypto) [8]**: Fields can be encrypted or signed to enforce access control across trust boundaries. OpenHW’s physical memory protection (PMP) and upcoming enhanced PMP (ePMP) can isolate Scheme memory regions, while cryptographic extensions can accelerate Field signature verification. This hardware‑assisted security complements SSCCS’s inherent structural isolation, creating a layered defence suitable for safety‑critical systems.

- **Multi‑core and Heterogeneous Integration [15]**: The CORE‑V family includes multi‑core configurations (e.g., CV32E40P dual‑core) and heterogeneous clusters. SSCCS’s immutability allows Schemes to be partitioned across cores without coherence overhead, enabling scalable observation across multiple compute units. The deterministic nature of observations ensures that results are independent of core scheduling, simplifying parallelisation.

These synergies illustrate that SSCCS is not merely a standalone extension but a programming model that can permeate the entire CORE‑V ecosystem, enhancing existing hardware features rather than replacing them.


## Current PoC Status and Readiness for OpenHW Integration

The SSCCS Proof of Concept (PoC) is a fully functional Rust‑based reference implementation that validates the core ontological layers of the model. The PoC has successfully passed ten constitutional concept tests, confirming that the abstract primitives—Segment, Scheme, Field, Observation, and Projection—can be realized as executable software. Key components already implemented include:

- **Core Library** (`ssccs‑core`): Defines `Segment` (immutable coordinate point with cryptographic identity), `Field` (mutable constraint substrate), `TransitionMatrix` (relational topology), and the `Projector` trait for semantic interpretation.
- **Scheme Abstraction Layer** (`ssccs‑primitive`): Provides a rich structural definition of `Scheme` with axis types (Discrete, Continuous, Cyclic, etc.), structural relations (Adjacency, Hierarchy, Dependency, Equivalence, Custom), memory‑layout mapping (Linear, Row‑Major, Space‑Filling Curve, etc.), and observation rules. Pre‑defined templates (Grid2D, IntegerLine, Graph) capture common topological patterns.
- **Compiler Pipeline Skeleton** (`ssccs‑primitive`): A four‑stage pipeline (parsing, structural analysis, memory‑layout resolution, hardware mapping) that translates high‑level Schemes into hardware‑specific layouts. The pipeline is target‑agnostic, ready to be extended with OpenHW‑specific backends.
- **Open Format Parser** (`ss_parser.rs`): A stub for the binary `.ss` format, ready to be fleshed out with full serialization/deserialization.
- **Research Crates** (`ssccs‑field‑synthesis`, `ssccs‑hardware‑mapping`, `ssccs‑compiler‑opt`): Placeholder crates for advanced research tracks, awaiting OpenHW‑specific investigations.

All ten constitutional tests pass, demonstrating that the SSCCS model is internally consistent and ready for external validation. The PoC thus provides a solid foundation for Phase 1 (software emulation) of the proposed collaboration. The existing Rust codebase can be immediately adapted to target the **riscvOVPsimCOREV** reference simulator, allowing SSCCS custom instructions to be exercised in a cycle‑accurate OpenHW core simulation.

**Readiness for OpenHW:** The PoC’s modular architecture separates the core SSCCS logic from hardware‑specific mapping, enabling a clean integration with the CORE‑V XIF interface. The `HardwareProfile` enum already includes a `GenericCPU` variant; adding a `COREV_XIF` variant is straightforward. The compiler’s hardware‑mapping stage can be extended to emit XIF‑compliant coprocessor descriptions, while the observation‑code generation stage can produce RISC‑V assembly that invokes custom `OBSERVE` instructions.


## Proposed Technical Roadmap (Enhanced with PoC‑Based Milestones)

### Phase 1: Software Emulation and Simulation

**Goal:** Establish a working SSCCS software stack that can target OpenHW CORE-V cores via simulation, building directly on the existing PoC.

**Activities:**
- Extend the PoC’s `HardwareProfile` enum with a `COREV_XIF` profile, capturing the XIF interface parameters (number of source registers, latency, etc.).
- Define a set of **observation primitives** (e.g., `OBSERVE`, `COLLAPSE`, `PROJECT`) as custom RISC‑V instructions using the R‑type format (opcode = `custom1` or `custom2`). The instruction semantics will mirror the PoC’s `observe` function, mapping Scheme‑ID, Field‑ID, and Segment‑ID registers to a projection result.
- Implement an SSCCS runtime library that translates structural descriptions (`.ss` files) into sequences of these custom instructions. The runtime will reuse the PoC’s `Scheme` and `Field` types, adding a thin translation layer that emits RISC‑V assembly.
- Integrate with **riscvOVPsimCOREV** (the Imperas reference simulator for OpenHW cores) to develop and test SSCCS custom instructions. The PoC’s existing test suite will be adapted to run on the simulator, comparing simulation outputs against the pure‑Rust reference results.
- Measure simulation accuracy and performance overhead of the observation primitives versus the Rust reference.

**Deliverables:**
- GitHub repository branch (`ssccs‑corev`) with SSCCS instruction‑set definitions and XIF‑aware hardware profile.
- Simulator‑ready test suite for core operations (vector addition, matrix multiplication, graph traversal) that passes on riscvOVPsimCOREV.
- Success metric: Validate 5 core primitives with <1% simulation error vs. theoretical model, and demonstrate that the custom‑instruction sequences produce identical projections to the Rust PoC.

### Phase 1.5: Verification IP Integration

**Goal:** Integrate SSCCS extensions into the CORE-V-VERIF verification environment to ensure compliance with OpenHW verification standards, leveraging the deterministic nature of SSCCS to reduce verification complexity.

**Activities:**
- Develop **UVM‑compliant test sequences** for SSCCS custom instructions within the CORE‑V‑VERIF framework. Each test will instantiate a Scheme and Field, issue the corresponding custom instruction, and compare the result against the Imperas reference model.
- Create reference models comparing SSCCS observation results against Imperas simulation outputs. Because SSCCS observations are deterministic, the reference model can be a simple pure function, drastically reducing the verification effort compared to traditional state‑ful coprocessors.
- Document verification coverage metrics for custom instruction paths. The immutability of Segments and Schemes eliminates whole classes of hazards (e.g., write‑after‑read, speculative side‑effects), allowing coverage closure with fewer test cases.
- Contribute the SSCCS verification components back to the CORE‑V‑VERIF repository as an example of how to verify deterministic, stateless custom extensions.

**Deliverables:**
- CORE‑V‑VERIF extension module for SSCCS instructions, including UVM sequences, scoreboards, and coverage collectors.
- Verification coverage report demonstrating compliance with OpenHW verification methodology.
- Success metric: Achieve 100% instruction coverage for SSCCS custom opcodes in UVM environment, with a 30% reduction in test‑case count compared to a state‑ful equivalent coprocessor.

### Phase 2: XIF Coprocessor Prototype

**Goal:** Implement a functional SSCCS coprocessor using the CORE-V XIF interface on an FPGA platform, translating the PoC’s observation logic into hardware.

**Activities:**
- Design a **XIF coprocessor module** that receives custom instructions from the CV32E40P core via the issue interface, performs the observation, and returns results via the result interface. The coprocessor will be **stateless** (as required by CVA6 recommendations), matching the SSCCS principle that observation does not modify internal state.
- Support up to **three source registers** (X_NUM_RS = 3) to accommodate complex structural operations (Scheme‑ID, Field‑ID, Segment‑ID). The coprocessor will decode the custom opcode and invoke the appropriate observation primitive.
- Implement **direct write‑back strategy** through XIF result interface, ensuring returned data follows standard pipeline forwarding paths without conflict with core register file operations.
- Map the PoC’s observation algorithm into hardware. The `TransitionMatrix` will be implemented as a small on‑chip SRAM, while constraint evaluation will use combinatorial logic. The coprocessor will be pipelined to match the core’s latency.
- Target the **CORE-V MCU DevKit** or a compatible FPGA platform (e.g., Nexys A7) for prototyping. Use the existing PoC test suite to generate verification vectors for the FPGA implementation.
- Benchmark results comparing SSCCS vs. standard RISC‑V implementations for key workloads (vector addition, matrix multiplication). Energy measurements will be obtained via FPGA power‑estimation tools.

**Deliverables:**
- Verilog/VHDL implementation of the SSCCS coprocessor, fully compliant with XIF specification.
- Integration guide for CORE-V users, showing how to instantiate the coprocessor in a CV32E40P‑based design.
- Benchmark results comparing SSCCS vs. baseline RISC‑V implementations for key workloads.
- Success metric: Demonstrate ≥3× energy reduction on vector addition vs. baseline RISC‑V, and achieve 95% functional correctness against the Rust reference.

### Phase 3: eFPGA Integration and MCU Validation

**Goal:** Demonstrate SSCCS running on the CORE-V MCU DevKit, leveraging the embedded FPGA (eFPGA) for hardware acceleration.

**Activities:**
- Map the observation logic into the **Quicklogic ArticPro 2 eFPGA** fabric integrated in the CORE-V MCU. The eFPGA will act as a reconfigurable accelerator, hosting multiple SSCCS coprocessor instances that can be swapped dynamically.
- Use the APB interface from the CV32E40P core to configure the eFPGA with SSCCS accelerators dynamically. The PoC’s compiler pipeline will be extended to generate eFPGA configuration bitstreams alongside ordinary machine code.
- Develop a demonstration application (e.g., real‑time sensor processing on the DevKit's Himax camera) that uses SSCCS to achieve measurable energy and latency gains. The application will define a Scheme representing the image sensor’ pixel array, a Field encoding region‑of‑interest constraints, and an observation that extracts features without moving raw pixel data.
- Measure end‑to‑end latency, energy consumption, and data‑movement reduction compared to a conventional C implementation running on the same MCU.

**Deliverables:**
- Open‑source eFPGA bitstream and configuration code for the CORE‑V MCU DevKit.
- Demonstration video and user guide showing the Himax camera pipeline running with SSCCS acceleration.
- Performance report quantifying data‑movement reduction and verifiability advantages.
- Success metric: Achieve <10 ms end‑to‑end latency on Himax camera pipeline with ≥2× energy gain versus pure‑software processing.

### Phase 4: Community Integration and Contribution

**Goal:** Upstream SSCCS components into OpenHW repositories and encourage broader adoption.

**Activities:**
- Contribute the SSCCS coprocessor design to the **CORE‑V‑VERIF** testbench as an example of custom extension verification.
- Propose a new **OpenHW Task Group** focused on structural programming models, using SSCCS as a starting point for standardising observation‑based extensions.
- Participate in OpenHW events and technical discussions to gather feedback and attract contributors.
- Prepare tutorial materials and workshops that teach OpenHW members how to integrate SSCCS into their own designs.

**Deliverables:**
- Pull requests accepted into OpenHW repositories (CORE‑V‑VERIF, CORE‑V‑SDK, documentation).
- Documentation and tutorials for OpenHW members to replicate the SSCCS integration.
- Success metric: Merge ≥2 PRs into CORE‑V‑VERIF; onboard ≥3 external contributors who independently use SSCCS on their own CORE‑V designs.


## Research Contributions to the OpenHW Ecosystem

Beyond the immediate technical deliverables, SSCCS brings several novel research directions that can enrich the OpenHW ecosystem:

### Verification Methodology for Deterministic Extensions
SSCCS’s deterministic execution model simplifies verification, a core concern for high‑volume production SoCs. By contributing SSCCS as a case study, we can help develop best practices for verifying stateless custom instructions—a pattern that will become increasingly important as RISC‑V extensions proliferate. The SSCCS verification IP can serve as a template for other extension developers, reducing the barrier to entry for custom hardware.

### Energy‑Efficient Computing through Structural Observation
The SSCCS model eliminates data movement by keeping Segments stationary and observing them in place. This aligns with OpenHW’s focus on energy‑efficient IoT and embedded systems. The collaboration will produce concrete measurements of energy savings on CORE‑V hardware, providing compelling evidence for structural observation as a viable path to break the “data‑movement wall.”

### Security and Safety by Construction
SSCCS’s immutable Segments and deterministic dataflow prevent whole classes of security vulnerabilities (e.g., speculative execution leaks, buffer overflows). These properties are especially valuable for OpenHW members targeting safety‑critical domains (automotive, industrial). The collaboration will demonstrate how SSCCS can be used to build ISO 26262‑compliant components with reduced verification overhead.

### Programming Model Innovation
SSCCS introduces a novel programming model—“structural observation”—that complements traditional imperative and dataflow models. By integrating SSCCS into the CORE‑V SDK, we provide OpenHW developers with a new way to express computation, potentially unlocking performance and energy benefits for certain problem classes (e.g., regular grids, graph algorithms, sensor‑fusion pipelines).

### Open Format Standardisation
The SSCCS `.ss` format is an open, binary representation of structural blueprints. By aligning this format with OpenHW’s open‑source philosophy, we can foster a community‑driven standard for describing computation as geometry. This standard could eventually be adopted by other RISC‑V extension developers, creating a common language for structural computing.


## Benefits for OpenHW and the CORE-V Ecosystem

| Benefit | Description |
|---------|-------------|
| **Novel Programming Model** | Adds "structural observation" to the CORE-V software stack, differentiating OpenHW cores from proprietary alternatives. |
| **Enhanced Verifiability** | SSCCS's deterministic execution simplifies verification – a core concern for high-volume production SoCs. |
| **Energy Efficiency Demonstration** | SSCCS's data-movement elimination can be showcased on OpenHW hardware, providing compelling evidence for energy-conscious designs. |
| **Security Enhancement** | Deterministic dataflow prevents speculative execution leaks and side-channel attacks. Immutability eliminates memory corruption vulnerabilities. |
| **Functional Safety Support** | Observation determinism enables ISO 26262-compliant traceability for automotive and industrial applications. |
| **Ecosystem Growth** | Attracts researchers and developers interested in foundational computing paradigms to the OpenHW community. |
| **Aligned with Member Interests** | OpenHW members (e.g., NXP, Silicon Labs, Thales) emphasize security, safety, and efficiency – all central to SSCCS. |


## Execution Team

This work will be led by Taeho Lee (Founder, SSCCS Foundation), with contributions from:

- **Compiler Engineering:** Backend development for `.ss` to RISC-V translation, leveraging experience in LLVM and GCC toolchains.
- **FPGA Architecture:** XIF coprocessor implementation and eFPGA integration, with prior work on RISC-V acceleration.
- **Formal Verification:** Academic advisors providing expertise in deterministic system verification and cryptographic auditability.

We welcome OpenHW members to co‑staff technical tasks and co‑author deliverables.


## Resource Requirements and Support Request

To execute this roadmap, SSCCS Foundation seeks:

| Support Type | Description |
|--------------|-------------|
| **Membership** | OpenHW membership (e.g., Silver or Gold level) to access technical working groups and contribute to the roadmap. |
| **Hardware Access** | Access to CORE-V MCU DevKit and FPGA platforms (e.g., Nexys A7) for validation. SSCCS Foundation can cover shipping and handling costs. |
| **Technical Collaboration** | Mentorship from OpenHW members experienced in XIF integration, eFPGA programming, and verification. |
| **Community Engagement** | Opportunities to present SSCCS at OpenHW events and workshops (e.g., OpenHW TV, technical meetings). |


## Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| **XIF interface complexity** | Start with minimal instruction set (2–3 primitives); expand iteratively based on validation feedback. Leverage the PoC’s modular design to isolate XIF‑specific code. |
| **eFPGA resource constraints** | Prioritize observation logic over storage; leverage external DRAM for large Schemes. Use the PoC’s memory‑layout abstraction to optimize eFPGA mapping. |
| **Verification overhead** | Leverage SSCCS's deterministic model to reduce test‑case explosion; contribute test vectors back to CORE‑V‑VERIF. |
| **Community adoption** | Co‑develop tutorials with OpenHW documentation team; host joint webinar post‑Phase 2. |
| **Schedule slippage** | Adopt agile milestones; deliver a minimal viable prototype after Phase 1 that can be demonstrated independently of later phases. |


## 10. Conclusion

SSCCS offers a unique opportunity to bring paradigm‑shifting research into the OpenHW ecosystem. By leveraging the **CORE-V XIF interface** and the **CORE-V MCU DevKit**, we can demonstrate how structural observation can complement conventional RISC-V cores, delivering improved verifiability and energy efficiency. This collaboration aligns with OpenHW's mission to drive innovation in open-source hardware and to provide a rich, accessible platform for the global semiconductor community.
 


## References

[1] OpenHW Group, "CORE-V eXtension Interface (XIF) Specification," 2025.

[2] OpenHW Group, "CORE-V-VERIF Verification Methodology," 2025.

[3] Imperas Software, "riscvOVPsimCOREV Reference Simulator Documentation," 2025.

[4] QuickLogic, "ArticPro 2 eFPGA Architecture Manual," 2025.

[5] T. Lee, "Schema–Segment Composition Computing System Whitepaper," DOI: 10.5281/zenodo.18759106, 2026.

[6] M. Horowitz, "Computing's Energy Problem (and What We Can Do About It)," IEEE ISSCC, 2014.

[7] A. Waterman et al., "The RISC-V Instruction Set Manual," 2019.

[8] OpenHW Group, "CV32E40P User Manual," 2024.

[9] W. A. Wulf and S. A. McKee, "Hitting the memory wall: implications of the obvious," *ACM SIGARCH Computer Architecture News*, vol. 23, no. 1, pp. 20–24, 1995.

[10] S. Borkar and A. A. Chien, "The future of microprocessors," *Communications of the ACM*, vol. 54, no. 5, pp. 67–77, 2011.

[11] R. Lucas et al., "Top ten exascale research challenges," U.S. Department of Energy, Tech. Rep., 2014.

[12] A. Gu and T. Dao, "Mamba: Linear-Time Sequence Modeling with Selective State Spaces," *arXiv preprint arXiv:2312.00752*, 2023.

[13] DeepSeek‑AI, "mHC: Manifold‑Constrained Hyper‑Connections," *arXiv preprint arXiv:2512.24880*, 2025.

[14] RISC‑V International, "RISC‑V Vector Extension Version 1.0," 2021.

[15] M. J. Flynn et al., "Parallel processing: breakthrough to supercomputing," *Proceedings of the IEEE*, vol. 96, no. 5, pp. 805–814, 2008.

[16] J. L. Hennessy and D. A. Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed. Morgan Kaufmann, 2017.

[17] S. B. Furber, *ARM System‑on‑Chip Architecture*, 2nd ed. Addison‑Wesley, 2000.

[18] A. M. G. Silva et al., "Formal verification of RISC‑V processors using UVM," in *2023 IEEE International Conference on Computer Design (ICCD)*, 2023, pp. 123–130.
 
## Appendix A: XIF Interface Signal Mapping

| XIF Signal | SSCCS Usage | Direction |
|------------|-------------|-----------|
| `issue_valid` | Instruction ready for observation | Core → Coprocessor |
| `issue_ready` | Coprocessor ready to accept | Coprocessor → Core |
| `issue_opcode` | SSCCS custom opcode (`custom1`/`custom2`) | Core → Coprocessor |
| `issue_rs1/rs2/rs3` | Segment/Scheme identifiers | Core → Coprocessor |
| `commit_valid` | Observation complete | Coprocessor → Core |
| `result_data` | Projection output | Coprocessor → Core |
| `result_exception` | Observation error flag | Coprocessor → Core |


## Appendix B: SSCCS Observation Instruction Format

```
31        25 24    20 19    15 14    12 11       7 6         0
+----------+----------+----------+----------+----------+----------+
|  imm[11:0]  |   rs3    |   rs2    |   rs1    |  custom1 |  opcode  |
+----------+----------+----------+----------+----------+----------+
|<-------- R-type Format for OBSERVE instruction --------------->|
```

**Opcode:** `custom1` (0x0B) or `custom2` (0x2B)  
**Function:** `OBSERVE rs1, rs2, rs3` → Load Scheme ID, Field ID, and Observation Rule

---

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research and engineering initiative building a computing model and compiler infrastructure.

- Whitepaper: [PDF](https://ssccs.org/wp) / [HTML](https://ssccs.org/wpw) DOI: [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg). Authenticated via GPG: [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99). Licensed under *Apache 2.0*. 
- Governed by the [Foundational Charter and Statute](https://ssccs.org/legal) of the SSCCS Foundation (in formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial review; full intellectual responsibility with author(s). All major outputs are [C2PA-certified](https://ssccs.org/wpc2pa).