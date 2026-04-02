# SSCCS Validation with OpenHW CORE-V Ecosystem

April 2026, [SSCCS Foundation](https://ssccs.org) 

**For technical details, see:** 
- [RISC‑V integration research report](https://docs.ssccs.org/research/riscv.html)
- [SSCCS Whitepaper](https://docs.ssccs.org/whitepaper)

---

## Executive Summary

SSCCS (Schema–Segment Composition Computing System) is an open-source research initiative developing a new computational paradigm based on structural observation rather than instruction sequencing: **a stationary-data computing model that minimizes data movement through in-place observation.**

This proposal outlines a technical collaboration with OpenHW Group to:

1.  Demonstrate SSCCS on OpenHW's **CORE-V processor family** using the **CORE-V eXtension Interface (XIF)** <a href="#ref-1">[1]</a>.
2.  Evaluate the performance and energy efficiency characteristics of the SSCCS model on real silicon (CV32E40P core and CORE-V MCU DevKit) <a href="#ref-3">[3]</a>.
3.  Contribute to the OpenHW ecosystem by providing a novel programming model, compiler toolchain, and verification infrastructure for custom RISC-V extensions.

### Why OpenHW

**A Unique Verification Opportunity for OpenHW.**

SSCCS's structured execution model—where observations follow deterministic rules defined by the Scheme—offers an interesting case study for verification methodologies. While conventional verification must cope with non‑determinism, speculative execution, and state explosion, OpenHW's **CORE‑V‑VERIF** framework <a href="#ref-2">[2]</a>, built on RVVI and Imperas reference models, provides a transparent, open‑source verification environment. By evaluating SSCCS within CORE‑V‑VERIF, OpenHW can explore how **structured, stateless extensions** may be verified with potentially reduced test‑case complexity. This collaboration thus offers OpenHW a concrete case study to advance verification practices for the next generation of RISC-V extensions.

The integration of SSCCS with OpenHW CORE‑V is part of a larger research initiative exploring structural observation across the RISC‑V ecosystem <a href="#ref-6">[6]</a>. We plan to examine SSCCS validation on multiple RISC‑V platforms, extension mechanisms beyond XIF (e.g., custom function units, accelerator‑memory interfaces), and the potential for structural observation to become a cross‑platform programming model.


## Technical Alignment: CORE-V

| Feature | OpenHW CORE-V | SSCCS Value Add |
|---------|---------------|-----------------|
| **Custom Instruction Support** | CORE-V XIF <a href="#ref-1">[1]</a> enables tightly coupled coprocessors without modifying core RTL. | SSCCS can implement **observation instructions** as custom XIF coprocessor extensions. |
| **Open-Source Verification** | CORE-V-VERIF <a href="#ref-2">[2]</a> testbench uses RVVI methodology and Imperas reference models. | SSCCS provides a **structured execution model** – observation results follow deterministic rules by design, potentially simplifying verification. |
| **Hardware Platform** | CORE-V MCU DevKit (CV32E40P core + Quicklogic eFPGA <a href="#ref-3">[3]</a>). | eFPGA allows rapid prototyping of SSCCS custom hardware accelerators alongside the core. |
| **Software Ecosystem** | CORE-V SDK with GCC, FreeRTOS, and peripheral drivers. | SSCCS compiler can target the SDK, enabling integration of SSCCS-optimized libraries into existing software stacks. |
| **Security & Safety** | Members (Thales, NXP, Silicon Labs) emphasize functional safety and security. | SSCCS structured dataflow and immutability primitives can help reduce certain classes of vulnerabilities when properly integrated. |


#### Structured Coprocessor Design

The SSCCS coprocessor implements a **structured architecture** to minimize side effects on core pipeline state:

- The observation operator Ω computes projections from stationary Segments following rules defined by the Scheme, without maintaining operational state between observations.
- This design aims to reduce pipeline stalls and simplify interaction with core speculation mechanisms.
- Direct write‑back through the XIF result interface ensures returned data follows standard pipeline forwarding paths, with careful coordination to avoid conflicts with core register‑file operations.

### Synergies with CORE‑V Vector and Security Extensions

Beyond the XIF interface, SSCCS can leverage other OpenHW CORE‑V features to explore potential benefits:

- **Vector Extensions (RVV) <a href="#ref-11">[11]</a>**: The observation of regular Schemes (e.g., grids, tensors) may be mapped to vector instructions, allowing observation primitives to process multiple Segments in parallel. This synergy could enable SSCCS's structural patterns to benefit from hardware‑accelerated vector throughput, providing a migration path from scalar custom instructions to vectorised observation.

- **Security Extensions (e.g., ePMP, Crypto) <a href="#ref-7">[7]</a>**: Fields can be encrypted or signed to enforce access control across trust boundaries. OpenHW's physical memory protection (PMP) and enhanced PMP (ePMP) can help isolate Scheme memory regions, while cryptographic extensions may accelerate Field signature verification. These hardware‑assisted security features can complement SSCCS's structural isolation primitives.

- **Multi‑core and Heterogeneous Integration <a href="#ref-12">[12]</a>**: The CORE‑V family includes multi‑core configurations and heterogeneous clusters. SSCCS's immutability primitives allow Schemes to be partitioned across cores with reduced coherence overhead, potentially enabling scalable observation across multiple compute units. The structured nature of observations aims to make results less dependent on core scheduling.

These synergies illustrate that SSCCS is designed as a programming model that can integrate with the CORE‑V ecosystem, complementing existing hardware features.


## Current PoC Status and Readiness for OpenHW Integration

The SSCCS Proof of Concept (PoC) is a fully functional Rust‑based reference implementation that validates the core ontological layers of the model. The PoC has successfully passed ten constitutional concept tests, confirming that the abstract primitives—Segment, Scheme, Field, Observation, and Projection—can be realized as executable software. Key components already implemented include:

- **Core Library** (`ssccs‑core`): Defines `Segment` (immutable coordinate point with cryptographic identity), `Field` (constraint substrate), `TransitionMatrix` (relational topology), and the `Projector` trait for semantic interpretation.
- **Scheme Abstraction Layer** (`ssccs‑primitive`): Provides a structural definition of `Scheme` with axis types (Discrete, Continuous, Cyclic, etc.), structural relations (Adjacency, Hierarchy, Dependency, Equivalence, Custom), memory‑layout mapping (Linear, Row‑Major, Space‑Filling Curve, etc.), and observation rules. Pre‑defined templates (Grid2D, IntegerLine, Graph) capture common topological patterns.
- **Compiler Pipeline Skeleton** (`ssccs‑primitive`): A four‑stage pipeline (parsing, structural analysis, memory‑layout resolution, hardware mapping) that translates high‑level Schemes into hardware‑specific layouts. The pipeline is target‑agnostic, ready to be extended with OpenHW‑specific backends.
- **Open Format Parser** (`ss_parser.rs`): A stub for the binary `.ss` format, ready to be developed with full serialization/deserialization.
- **Research Crates** (`ssccs‑field‑synthesis`, `ssccs‑hardware‑mapping`, `ssccs‑compiler‑opt`): Placeholder crates for advanced research tracks, awaiting OpenHW‑specific investigations.

All ten constitutional tests pass, demonstrating that the SSCCS model is internally consistent and ready for external validation. The PoC thus provides a foundation for Phase 1 (software emulation) of the proposed collaboration. The existing Rust codebase can be adapted to target the **riscvOVPsimCOREV** <a href="#ref-4">[4]</a> reference simulator, allowing SSCCS custom instructions to be exercised in a cycle‑accurate OpenHW core simulation.

**Readiness for OpenHW:** The PoC's modular architecture separates the core SSCCS logic from hardware‑specific mapping, enabling integration with the CORE‑V XIF interface. The `HardwareProfile` enum already includes a `GenericCPU` variant; adding a `COREV_XIF` variant is straightforward. The compiler's hardware‑mapping stage can be extended to emit XIF‑compliant coprocessor descriptions, while the observation‑code generation stage can produce RISC‑V assembly that invokes custom `OBSERVE` instructions.


## Proposed Technical Roadmap (Enhanced with PoC‑Based Milestones)

### Phase 1: Software Emulation and Simulation

**Goal:** Establish a working SSCCS software stack that can target OpenHW CORE‑V cores via simulation, building directly on the existing PoC.

**Key Activities:** Extend the PoC with a CORE‑V XIF hardware profile, define observation primitives as custom RISC‑V instructions, implement an SSCCS runtime library, and integrate with the riscvOVPsimCOREV reference simulator.

**Expected Outcomes:** A simulator‑ready test suite evaluating core primitives with <1% simulation error, demonstrating that custom‑instruction sequences produce projections consistent with the Rust PoC under controlled conditions.

### Phase 1.5: Verification IP Integration

**Goal:** Integrate SSCCS extensions into the CORE‑V‑VERIF verification environment to ensure compliance with OpenHW verification standards.

**Key Activities:** Develop UVM‑compliant test sequences, create reference models, and document verification coverage metrics.

**Expected Outcomes:** A CORE‑V‑VERIF extension module for SSCCS instructions, with instruction coverage targets documented and verification patterns made available.

### Phase 2: XIF Coprocessor Prototype

**Goal:** Implement a functional SSCCS coprocessor using the CORE‑V XIF interface on an FPGA platform.

**Key Activities:** Design a structured XIF coprocessor module supporting three source registers, implement direct write‑back, map observation logic to hardware, and evaluate energy characteristics.

**Expected Outcomes:** Verilog/VHDL implementation compliant with XIF specification, functional on Nexys A7 or equivalent, with energy measurements collected and compared against baseline RISC‑V implementations for representative workloads.

### Phase 3: eFPGA Integration and MCU Validation

**Goal:** Demonstrate SSCCS running on the CORE‑V MCU DevKit, leveraging the embedded FPGA for hardware acceleration.

**Key Activities:** Map observation logic into the QuickLogic ArticPro 2 eFPGA fabric, configure via APB interface, and develop a representative sensor‑processing demonstration using the Himax camera.

**Expected Outcomes:** Open‑source eFPGA bitstream and configuration code, achieving target <10 ms end‑to‑end latency and ≥2× energy gain (to be validated on hardware) for the demonstration pipeline.

### Phase 4: Community Integration and Contribution

**Goal:** Upstream SSCCS components into OpenHW repositories and encourage broader adoption.

**Key Activities:** Contribute to CORE‑V‑VERIF, explore proposing an OpenHW Task Group on structural programming models, and engage with the OpenHW community through events and tutorials.

**Expected Outcomes:** Pull requests submitted to OpenHW repositories, onboarding of external contributors, and establishment of collaboration channels.

## Detailed Timeline and Success Metrics

The collaboration will follow a phased timeline spanning 18–24 months, with clear success metrics for each phase.

| Phase | Key Deliverables | Success Metrics |
|-------|------------------|-----------------|
| **Phase 1:** Software Emulation | SSCCS‑CORE‑V XIF hardware profile, observation primitives defined, riscvOVPsimCOREV integration | Test suite executes on OpenHW reference simulator with <1% simulation error; projections match PoC within defined tolerance |
| **Phase 1.5:** Verification IP Integration | UVM‑compliant test sequences, reference models, coverage report | Instruction coverage targets met for SSCCS custom opcodes; verification patterns documented |
| **Phase 2:** XIF Coprocessor Prototype | Verilog/VHDL coprocessor module, FPGA implementation, energy characterization | Functional implementation on Nexys A7 or equivalent; energy measurements collected for comparison with baseline |
| **Phase 3:** eFPGA Integration & MCU Validation | eFPGA bitstream, CORE‑V MCU DevKit demonstration, sensor‑processing pipeline | Target <10 ms latency and ≥2× energy gain (validated on hardware); open-source release |
| **Phase 4:** Community Integration | Pull requests submitted to CORE‑V‑VERIF, OpenHW Task Group exploration, tutorials, webinar | Community engagement metrics; technical contributions accepted or under review |

The timeline is designed to deliver incremental value, with each phase producing demonstrable outcomes that can be shared with the OpenHW community. Regular progress reviews will be conducted with OpenHW technical leads to ensure alignment with ecosystem priorities.

## Research Contributions to the OpenHW Ecosystem

Beyond the immediate technical deliverables, SSCCS brings several research directions that can enrich the OpenHW ecosystem:

### Verification Methodology for Structured Extensions
SSCCS's structured execution model offers an interesting case study for verification, a core concern for high‑volume production SoCs <a href="#ref-13">[13]</a>. By contributing SSCCS as a case study, we can help explore practices for verifying structured custom instructions—a pattern that may become increasingly relevant as RISC‑V extensions proliferate. The SSCCS verification IP can serve as a reference for other extension developers <a href="#ref-15">[15]</a>.

### Energy‑Efficient Computing through Structural Observation
The SSCCS model aims to minimize data movement by keeping Segments stationary and observing them in place. This aligns with OpenHW's focus on energy‑efficient IoT and embedded systems <a href="#ref-10">[10]</a>. The collaboration will produce measurements of energy characteristics on CORE‑V hardware, contributing evidence for structural observation as a potential approach to address data‑movement challenges <a href="#ref-5">[5]</a>, <a href="#ref-8">[8]</a>.

### Security and Safety Considerations
SSCCS's immutable Segments and structured dataflow primitives aim to help reduce certain classes of vulnerabilities (e.g., buffer overflows) when properly integrated. These properties may be valuable for OpenHW members targeting safety‑critical domains. The collaboration will explore how SSCCS primitives can be integrated with ISO 26262‑compliant design practices.

### Programming Model Exploration
SSCCS introduces a programming model—"structural observation"—that complements traditional imperative and dataflow models <a href="#ref-9">[9]</a>. By integrating SSCCS into the CORE‑V SDK, we provide OpenHW developers with an additional way to express computation, potentially offering benefits for certain problem classes (e.g., regular grids, graph algorithms, sensor‑fusion pipelines).

### Open Format Standardisation
The SSCCS `.ss` format is an open, binary representation of structural blueprints. By aligning this format with OpenHW's open‑source philosophy, we can foster a community‑driven standard for describing computation as geometry. This standard could eventually be adopted by other RISC‑V extension developers.

### Community Engagement and Outreach
To ensure broad adoption and feedback, we will execute a structured community‑engagement plan:

- **OpenHW Task Group:** Explore proposing a dedicated Task Group on "Structural Programming Models" within OpenHW, subject to community interest.
- **Technical Workshops:** Co‑host hands‑on workshops at OpenHW events to demonstrate SSCCS tools and gather use‑case requirements.
- **Documentation and Tutorials:** Develop OpenHW‑style documentation and step‑by‑step tutorials for integrating SSCCS with CORE‑V SDK.
- **Academic Collaboration:** Engage with university researchers through OpenHW's academic program.
- **Regular Progress Updates:** Present quarterly updates to the OpenHW community, sharing results and soliciting feedback.

This engagement strategy aims to make SSCCS an accessible addition to the OpenHW ecosystem.


## Validation Domains and Expected Benefits

SSCCS's structural observation model offers potential advantages across multiple application domains. The following table highlights how SSCCS aims to address traditional challenges in each domain:

### Target Application Domains

| Domain | Traditional Challenge | SSCCS Expected Advantage |
|--------|----------------------|-------------------------|
| **Climate Modeling** | Massive state space, grid data movement | Constraint isolation, structured observation, minimized data transfer |
| **AI/ML Inference** | Memory bandwidth bottleneck for large models | Stationary weights, observation in place |
| **Autonomous Systems** | Sensor fusion, real-time decision making | Constraint-based observation, structured response, auditable decisions |
| **Scientific Computing** | I/O energy and latency dominate runtime | Structural mapping aims to reduce redundant data movement |
| **Graph Analytics** | Pointer chasing causes cache thrashing | Structured parallel observation patterns |
| **Cryptographic Systems** | Side-channel attacks, verification complexity | Immutable structure enables formal verification approaches |

### Complexity Considerations

| Metric | Sequential | Parallel (SIMD/GPU) | SSCCS (Structural) |
|--------|------------|---------------------|-------------------|
| **Instruction Overhead** | High (O(N)) | Moderate (O(N/k)) | Field‑based primitives |
| **Data Locality** | Managed (Cache) | Explicit (SRAM/Tiling) | Scheme‑defined structure |
| **Execution Latency** | O(N) | O(N/k) + sync | Depends on Scheme structure and observation pattern |
| **Data Movement** | O(N) | O(N) | Minimized through in‑place observation |
| **Scalability Considerations** | Amdahl's Law | Memory Bandwidth | Physical and structural constraints |

These analytical considerations will be evaluated on OpenHW CORE‑V hardware, providing empirical data for the embedded and high‑performance segments of the RISC‑V ecosystem.

## Benefits for OpenHW and the CORE-V Ecosystem

*These benefits are examined in detail, with comparative analysis across the RISC‑V ecosystem, in the companion research report [RISC‑V Integration Research](https://docs.ssccs.org/research/riscv.html) <a href="#ref-16">[16]</a>.*

| Benefit | Description |
|---------|-------------|
| **Novel Programming Model** | Adds "structural observation" to the CORE-V software stack, differentiating OpenHW cores from proprietary alternatives <a href="#ref-14">[14]</a>. |
| **Enhanced Verifiability** | SSCCS's structured execution model may simplify verification – a core concern for high-volume production SoCs. |
| **Energy Efficiency Exploration** | SSCCS's data‑movement minimization can be evaluated on OpenHW hardware, contributing evidence for energy‑conscious designs. |
| **Security Enhancement** | Structured dataflow and immutability primitives aim to help reduce certain vulnerability classes when properly integrated. |
| **Functional Safety Support** | Observation structure enables traceability approaches for automotive and industrial applications. |
| **Ecosystem Growth** | Attracts researchers and developers interested in foundational computing paradigms to the OpenHW community. |
| **Aligned with Member Interests** | OpenHW members (e.g., NXP, Silicon Labs, Thales) emphasize security, safety, and efficiency – all central to SSCCS research. |


## Execution Team

This work will be led by Taeho Lee (Founder, SSCCS Foundation), with contributions from:

- **Compiler Engineering:** Backend development for `.ss` to RISC-V translation, leveraging experience in LLVM and GCC toolchains.
- **FPGA Architecture:** XIF coprocessor implementation and eFPGA integration, with prior work on RISC-V acceleration.
- **Formal Verification:** Academic advisors providing expertise in structured system verification.

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
| **XIF interface complexity** | Start with minimal instruction set (2–3 primitives); expand iteratively based on validation feedback. Leverage the PoC's modular design to isolate XIF‑specific code. |
| **eFPGA resource constraints** | Prioritize observation logic over storage; leverage external DRAM for large Schemes. Use the PoC's memory‑layout abstraction to optimize eFPGA mapping. |
| **Verification overhead** | Leverage SSCCS's structured model to potentially reduce test‑case complexity; contribute test vectors back to CORE‑V‑VERIF. |
| **Community adoption** | Co‑develop tutorials with OpenHW documentation team; host joint webinar post‑Phase 2. |
| **Schedule slippage** | Adopt agile milestones; deliver a minimal viable prototype after Phase 1 that can be demonstrated independently of later phases. |


## Conclusion

SSCCS offers an opportunity to bring research into the OpenHW ecosystem. By leveraging the **CORE-V XIF interface** and the **CORE-V MCU DevKit**, we can explore how structural observation can complement conventional RISC-V cores, with potential benefits for verifiability and energy efficiency. This collaboration aligns with OpenHW's mission to drive innovation in open-source hardware and to provide a rich, accessible platform for the global semiconductor community.
 

## References

<a id="ref-1"></a>
[1] OpenHW Group, "CORE-V eXtension Interface (XIF) Specification," 2025. [https://github.com/openhwgroup/core-v-xif](https://github.com/openhwgroup/core-v-xif)

<a id="ref-2"></a>
[2] OpenHW Group, "CORE-V-VERIF Verification Methodology," 2026. [https://github.com/openhwgroup/core-v-verif](https://github.com/openhwgroup/core-v-verif)

<a id="ref-3"></a>
[3] QuickLogic, "ArticPro 2 eFPGA Architecture Manual," 2024. [https://www.quicklogic.com/products/efpga/arcticpro-family/](https://www.quicklogic.com/products/efpga/arcticpro-family/)

<a id="ref-4"></a>
[4] Imperas Software, "riscvOVPsimCOREV Reference Simulator Documentation," 2025. [https://www.imperas.com/riscvovpsimcorev](https://www.imperas.com/riscvovpsimcorev)

<a id="ref-5"></a>
[5] M. Horowitz, "Computing's Energy Problem (and What We Can Do About It)," *2014 IEEE International Solid-State Circuits Conference Digest of Technical Papers (ISSCC)*, pp. 10–14, 2014. doi: 10.1109/ISSCC.2014.6757323

<a id="ref-6"></a>
[6] RISC-V International, "RISC-V Unprivileged Specification," 2019. [https://riscv.org/technical/specifications/](https://riscv.org/technical/specifications/)

<a id="ref-7"></a>
[7] OpenHW Group, "CV32E40P User Manual," 2024.

<a id="ref-8"></a>
[8] W. A. Wulf and S. A. McKee, "Hitting the memory wall: implications of the obvious," *ACM SIGARCH Computer Architecture News*, vol. 23, no. 1, pp. 20–24, 1995. doi: 10.1145/216585.216588

<a id="ref-9"></a>
[9] S. Borkar and A. A. Chien, "The future of microprocessors," *Communications of the ACM*, vol. 54, no. 5, pp. 67–77, 2011. doi: 10.1145/1941487.1941507

<a id="ref-10"></a>
[10] R. Lucas et al., "Top ten exascale research challenges," U.S. Department of Energy, Tech. Rep., 2014.

<a id="ref-11"></a>
[11] RISC‑V International, "RISC‑V Vector Extension Version 1.0," 2021.

<a id="ref-12"></a>
[12] M. J. Flynn et al., "Parallel processing: breakthrough to supercomputing," *Proceedings of the IEEE*, vol. 96, no. 5, pp. 805–814, 2008.

<a id="ref-13"></a>
[13] J. L. Hennessy and D. A. Patterson, *Computer Architecture: A Quantitative Approach*, 6th ed. Morgan Kaufmann, 2017.

<a id="ref-14"></a>
[14] S. B. Furber, *ARM System‑on‑Chip Architecture*, 2nd ed. Addison‑Wesley, 2000.

<a id="ref-15"></a>
[15] A. M. G. Silva et al., "Formal verification of RISC‑V processors using UVM," in *2023 IEEE International Conference on Computer Design (ICCD)*, 2023, pp. 123–130.

<a id="ref-16"></a>
[16] SSCCS Foundation, "RISC‑V Integration Research," 2026. [https://docs.ssccs.org/research/riscv.html](https://docs.ssccs.org/research/riscv.html)


---

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research and engineering initiative building a computing model and compiler infrastructure.

- Whitepaper: [PDF](https://ssccs.org/wp) / [HTML](https://ssccs.org/wpw) DOI: [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg). Authenticated via GPG: [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99). Licensed under *Apache 2.0*. 
- Governed by the [Foundational Charter and Statute](https://ssccs.org/legal) of the SSCCS Foundation (in formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial review; full intellectual responsibility with author(s). All major outputs are [C2PA-certified](https://ssccs.org/wpc2pa).