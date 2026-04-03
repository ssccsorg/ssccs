# Project Direction

Toward a New Computational Paradigm Verifiable by Open Hardware, and Regionally Informed Global Engagement

SSCCS is a software-defined revolution enabled by open hardware. Our journey is about defining the language that future processors will speak. By focusing on the purity of our computational model and using open hardware as our proving ground, we invite the world to move beyond the limitations of the past.

## Background and Rationale

We have engaged with a wide range of funding bodies, research institutions, and open‑source programmes across different regions. These interactions have been invaluable for clarifying the project’s vision and refining its documentation. At the same time, they have underscored a fundamental mismatch between most conventional funding mechanisms and a project like SSCCS.

The majority of these programmes are designed for:

- Already mature open‑source libraries or toolchains based on the current environment to expose it immediately.
- Consortia dominated by commercial entities with clear go‑to‑market plans.
- Incremental improvements within the established von Neumann paradigm.

SSCCS, by contrast, is not a library or a framework—it is a new computational foundation. It questions the very assumptions on which current hardware and software stacks are built. As such, it is inherently too early‑stage and too foundational for many conventional funding streams, which tend to reward proven, narrowly scoped deliverables rather than paradigm‑shifting research.

Our approach has evolved from seeking abstract validation to actively building the future of computation within the living ecosystem of open hardware and the software that runs on it.

## A New Compass: The Open Hardware Wave

The global technology landscape is changing. The rise of open instruction set architectures (ISAs) has fundamentally altered how new computing ideas can be realised. Unlike proprietary architectures, open ISAs offer:

- Full transparency: specifications are open, and implementations can be freely studied, modified, and extended.
- A rapidly growing ecosystem: from academic research groups to industry consortia, a vibrant community is actively building the next generation of processors.
- Tangible, concrete targets: real silicon and FPGA platforms exist today, allowing experimental computing models to be tested on actual hardware.

This shift creates an unprecedented opportunity. Instead of spending months on paperwork to *ask* for support, we can now directly *engage* with the ecosystem where new hardware is being built. In this context, our goal is no longer to secure abstract “funding” but to become a visible contributor to a living technological movement—through software that makes hardware easier to program.

## Regional Realities

Different regions exhibit distinct industrial cultures, strategic priorities, and modes of collaboration. To be effective, we must adapt our engagement style while remaining true to our core principles.

### Asia‑Pacific (including China, Singapore/ASEAN, Korea, Japan)
- Characteristics: High pace of implementation, strong government‑backed initiatives, and a pragmatic focus on building independent technology stacks. Cross‑border collaboration is common and often encouraged.
- Strategic Emphasis: Speed to silicon, ecosystem building, and long‑term technological sovereignty. By 2026, open ISAs are seeing large‑scale deployments in AI‑optimised data centres and edge‑AI. Traditional grant cycles often fail to keep pace with APAC’s “concept‑to‑silicon” speed, which for FPGA‑backed prototypes can be as short as 6–9 months.
- Engagement Strategy: Offer concrete software contributions (compiler passes, runtime libraries) that target these hardware platforms. Be open to joint prototyping where our software stack runs on real silicon, and position SSCCS as a complementary layer that enhances programmability and verifiability. Emphasise tangible results (e.g., FPGA‑accelerated demos within 6–9 months) and shared technical goals rather than lengthy administrative processes.

### Europe
- Characteristics: Strong emphasis on open‑source values, digital sovereignty, and predictable, verifiable systems. Funding programmes favour consortia and incremental progress.
- Strategic Emphasis: Formal correctness, security, and energy efficiency. European research groups excel in formal methods, real‑time systems, and compiler verification.
- Engagement Strategy: Collaborate with specific research groups working on time‑predictable architectures or formal verification, leveraging our native Rust implementation for rigorous mathematical validation. Use Europe as a source of deep technical collaboration and academic validation, not as the primary funding pipeline.

### North America
- Characteristics: A mix of university research, corporate R&D, and private venture capital. Result‑oriented culture valuing clear pathways to commercialisation.
- Strategic Emphasis: Performance, scalability, and integration with existing software ecosystems.
- Engagement Strategy: Target research labs and open‑source foundations supporting foundational infrastructure. Focus on technical demonstration and community building; be prepared to show clear “what’s in it for them” in terms of technical benefit or research impact.

### Middle East
- Characteristics: Rapidly growing technology investment driven by national diversification strategies. Interest in emerging technologies (AI, semiconductors) with a long‑term horizon.
- Strategic Emphasis: Building local capability, attracting international talent, and participating in large‑scale national initiatives.
- Engagement Strategy: Approach through targeted academic partnerships with centres of excellence (e.g., KAUST, MBZUAI, QCRI). Emphasise SSCCS’s potential as a foundational software stack for sovereign AI computing.

### Summary
Each region offers different opportunities. Success lies in building a portfolio of relationships that reflect our technical nature: a verified, open software initiative ready for hardware integration.

## Where SSCCS Fits: Bridging the ISA Gap

SSCCS is first and foremost a software project—a compiler, a runtime, and a declarative format that allows computation to be expressed as stationary structure. It is designed to target multiple hardware backends, from conventional CPUs to emerging open‑hardware platforms.

- Hardware needs a programming model. Open instruction sets provide the “what”. SSCCS provides the “how”—a way to describe computation as geometric structure and automatically map it to the underlying hardware through a dedicated compiler.
- Verifiability is a requirement, not a luxury. As safety‑critical systems grow, demand for deterministic computation increases. SSCCS offers verifiability by design, built into its core semantics.
- Energy efficiency is a first‑order constraint. Data movement is the dominant energy sink. By eliminating it through structural isolation, SSCCS addresses physical limits facing chip designers—without requiring hardware changes.

In the current landscape—driven by agentic AI and HPC—SSCCS solves:
1. Deterministic latency for safety‑critical applications.
2. The von Neumann bottleneck, bypassing data‑movement costs through software‑driven structural mapping.

### Technical Synchronisation: Platforms That Fit
To transition from pure‑software simulation to tangible hardware validation, we will target specific open‑hardware platforms with broad community adoption. These will serve as demonstration targets for our compiler and runtime, not as the primary development environment.

- CVA6 (OpenHW Group): Target for “Safe” dual‑core lock‑step components, aligning with our verifiability goals. Our compiler will emit code that leverages its safety features.
- CORE‑V Wally: An academic 5‑stage pipeline ideal for validating structural mapping concepts. We will use it to measure the impact of our compiler optimisations.
- Vector & Graph Extensions: Leveraging RISC‑V Vector (RVV) to demonstrate energy‑per‑op gains for graph‑like computations inherent in our model.

Key architectural decision: Develop a target‑agnostic execution interface (HAL) within the codebase. This layer will abstract the underlying execution engine, allowing the core SSCCS logic (parser, analyser, layout resolver) to remain unchanged while swapping the backend between:
- The current pure‑Rust simulator.
- A future RISC‑V custom instruction dispatcher (via inline assembly or C FFI).
- FPGA‑accelerated co‑processors.

This ensures that the ontological core requires zero rewrites when porting to physical silicon, keeping the project fundamentally a software initiative.

## Our Fundamental Stance: Win‑Win Without Chasing Short‑Term Profit

Throughout all engagements, we maintain consistent principles:
- Win‑win orientation: Partnerships where both sides gain technically or strategically. We are not a one‑way transaction.
- Beyond immediate profitability: Market fit is secondary to reshaping computation. We prioritise partners who respect this long‑term perspective.
- Open to serious collaboration, closed to superficial evaluation: We welcome scrutiny of our technical decisions and consensus‑based governance. We invest time only where there is genuine interest in our unconventional, early‑stage idea.

## Immediate Action Plan

### Technical Integration (Cross‑Regional)
- Maintain software‑first development: Continue refining the Rust compiler, runtime, and open format. Keep the codebase clean and modular.
- Select concrete open‑hardware platforms for validation: Target CVA6, CORE‑V Wally, and Vector extensions as demonstration backends.
- Port SSCCS concepts to these platforms:
  - *Phase 1*: Define structural mapping as custom instructions/co‑processor extensions via simulation (QEMU or custom emulator).
  - *Phase 2*: Move to FPGA prototypes running real examples (vector addition, graph algorithms) to validate performance and energy claims.
- Prioritise Scope: Focus strictly on one primary target initially to ensure delivery within 6–9 months, mitigating resource risks.
- Publish open‑source tools: Release the stack with clear documentation. A working demonstration on FPGA carries more weight than extensive whitepapers.

### Community Engagement (Regional Focus)
- In Asia‑Pacific: Engage forums with working prototypes. Highlight rapid “concept‑to‑silicon” potential and the ease of integrating our software stack with their hardware.
- In Europe: Share formal specifications with verification groups for deep technical exchange. Our Rust codebase is well‑suited for formal reasoning.
- In North America: Connect with foundations emphasising native integration benefits. Emphasise that our software is ready to be adopted by hardware projects.
- In the Middle East: Initiate outreach to key innovation hubs for joint research tracks, offering to adapt our software to their hardware needs.

### Partnership Without Dependency
- We seek collaborators, not sponsors: Identify groups active in open‑hardware interested in novel programming models.
- We offer technology, not a request: We are developing a new way to program open hardware. Our software stack is already functional on simulation; so looking for partners to help validate it on real silicon.
- Organic Evolution: Let partnerships grow from technical alignment, not application forms.

### Licensing Compatibility
Our code is licensed under Apache 2.0, aligning perfectly with open‑hardware norms (Solderpad/Apache). This removes legal friction, making it easier for hardware projects to integrate SSCCS components without compatibility concerns.

### Resource Sustainability
Recognising the need to fund the transition to FPGA validation:
- Micro‑Grants & Bounties: Pursue targeted grants for specific milestones (e.g., completing the CVA6 backend).
- In‑Kind Support: Prioritise partnerships offering FPGA cloud access or engineering time.
- Lean Operations: Maintain a lean model to bridge the initial prototyping phase independently.

## Long‑Term Vision & Success Metrics

The goal: Establish a new computational foundation where structure is the primitive, expressed through open‑source software and eventually adopted by hardware designers.

- Short term (0–12 months): Demonstrate a working prototype on open hardware, with our software stack running on a real FPGA.
  - *Success Metric*: A merged Pull Request into a major open‑hardware repo, independent teams running our simulator, and one joint technical paper.
- Medium term (1–3 years): Expand to complex AI/graph workloads, demonstrating measurable efficiency gains compared to traditional software stacks on the same hardware.
- Long term (3+ years): Contribute to standardisation (e.g., RISC‑V extensions, open format specifications), providing clear specs and reference implementations for global adoption.

Success is measured by adoption, not grant size. If future core designers consider “structural observation” natural, and software developers reach for defining scheme-segment to describe computational structure, we succeed.

## Conclusion

SSCCS is at its core a technological project. Its value lies not in the number of proposals submitted, but in the quality of its ideas and the clarity with which they are demonstrated. The current global momentum around open instruction set architectures offers a unique opportunity to embed SSCCS into a living ecosystem where new hardware is being built.

Not only application‑centric funding channels, but we focus on direct technical engagement with hardware designers and system builders, we turn the project’s strength—its foundational nature—into its primary asset. We will approach each region with respect, seeking win‑win relationships with partners willing to engage seriously with our nascent idea. The immediate goal is no longer to write another proposal, but to produce a tangible, open‑source artifact that the community can see, run, and build upon.

---

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research and engineering initiative building a computing model and compiler infrastructure.

- Whitepaper: [PDF](https://ssccs.org/wp) / [HTML](https://ssccs.org/wpw) DOI: [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg). Authenticated via GPG: [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99). Licensed under *Apache 2.0*. 
- Governed by the [Foundational Charter and Statute](https://ssccs.org/legal) of the SSCCS Foundation (in formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial review; full intellectual responsibility with author(s). All major outputs are [C2PA-certified](https://ssccs.org/wpc2pa).