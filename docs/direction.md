# Project Direction

## Toward a New Computational Paradigm

For decades, computation has been defined by the von Neumann model: data and instructions stored in memory, fetched sequentially, executed by a processor, with results written back. The majority of energy and time in such systems is spent on data movement rather than logic—the well-known "data-movement wall." SSCCS proposes a shift from procedural execution to structural observation, as a redefinition of what computation is. For details, see:

- [Guide](/guide.html)
- [Whitepaper](/whitepaper/whitepaper.html)
- [Public Proposal](/proposal/proposal.html)

This document outlines how SSCCS translates its philosophical and technical foundations into a concrete engineering trajectory, how we organise our work culturally, and how we engage with the global ecosystem to realise this paradigm in practice.

> **Summary**: SSCCS is a software-first initiative redefining computation as structural observation. We seek technical collaborators—not sponsors—to validate our compiler and runtime on open-hardware platforms. Our culture prioritises human wellbeing, results over process, and open contribution. If you share this vision, let us build.

## Cultural Foundations

### Human Comes First
All tools—rules, processes, methodologies, AI, automation, workflows—exist solely to support the goal of project, contributor's work and life. They are means, never ends. If a procedure causes unnecessary stress, fatigue, or alienation, the procedure is wrong—not the human. Our project goal and technology exists to help people live better, not despite it. Conversely, even claims of moral superiority cannot precede the project or its members. No ideology or virtue signaling stands above the wellbeing of the people doing the work.

### Results-Oriented Pragmatism
Code quality, maintainability, and system impact matter more than how the code was written. We bypass bureaucracy and exhausting debates. Prove your point with code. Discussions are limited to software engineering, architecture, and performance. Unrelated ideological or social agendas will be ignored.

### Clarity of Responsibility
Every contributor bears 100% responsibility for their contributions. Tools (including AI) are aids; the human engineer remains accountable. In 2026, AI use is as standard as a compiler. We do not mandate disclosure—only evaluate correctness, security, and test compliance. We encourage its use if it supports our project's healthy growth.

### Beyond Boundaries
We acknowledge that even our hosting platforms operate within centralized constraints. Where possible, we choose open, decentralized alternatives. We encourage bold ideas that challenge conventional computing—provided they do not block other contributors.

These principles are complementary: we pursue results through sustainable collaboration, not at its expense. Rigorous technical debate is welcome; personal pressure is not. See more at [Code of Conduct](/code_of_conduct.html)


## Partnership, Collaboration, and Support

SSCCS does not await institutional validation to proceed. But we engage directly with academia, industry, open‑hardware communities, and independent researchers, guided by technical merit and reciprocal contribution. We seek collaborators, not patrons; co‑creators, not auditors.

We have engaged with funding bodies, research institutions, and open‑source initiatives across multiple regions. These dialogues have been instrumental in clarifying our vision and refining our documentation, yet they have also revealed a structural mismatch between conventional funding mechanisms and a project like SSCCS.

Most established programmes are optimised for predictability. They typically support:

- Mature open‑source libraries or toolchains operating within existing paradigms;
- Commercial consortia with defined go‑to‑market strategies;
- Incremental advances that reinforce the von Neumann architecture.

SSCCS does not iterate within an established stack; it reimagines the substrate of computation itself. Because it questions foundational assumptions about hardware, software, and information flow, it is inherently too early‑stage and too conceptually disruptive for mechanisms that reward narrow, near‑term deliverables. Institutional risk‑aversion and paradigm‑shifting research are, by design, misaligned.

This reality shapes our posture. Rather than retrofitting our work to fit funding templates, we prioritise collaboration grounded in technical substance, epistemic openness, and long‑term vision. Genuine innovation does not emerge from centralised approval; it crystallises through iterative contribution within an open ecosystem. The technological foundations we rely on today were not mandated by sovereign committees. They emerged from a borderless, decentralised commons—built by countless contributors who treated code as a shared inheritance. To now frame foundational progress through the lens of technological sovereignty is to confuse geopolitical strategy with the actual mechanics of innovation.

Our engagement is guided by three principles:

- Reciprocal value: Partnerships must generate technical or strategic benefit for all parties. We do not operate as one‑way conduits.
- Foundational over immediate: Market fit is secondary to redefining computation. We align with partners who share a long‑term, systems‑level perspective.
- Substance over ceremony: We welcome rigorous technical scrutiny and consensus‑based governance, but we invest only where there is genuine commitment to early‑stage, paradigm‑shifting work.

Where funding is required, we view it as a catalyst for our mission rather than a primary objective. Our approach is guided by a clear priority: focusing on tangible progress and substantive research over administrative complexity. While our methods remain flexible to respect local industrial cultures and collaboration norms, our core commitments are steadfast. We prioritise technical depth, long-term vision, and mutual partnership as the foundations of our work. By streamlining our engagement and focusing on direct technical merit, we ensure that our energy remains dedicated to innovation.

Our goal is to build a computational commons that is open to everyone, regardless of geography or institutional background. We invite those who share this vision to join us in shaping this new foundation for computation. For collaboration details, see our [Code of Conduct](/code_of_conduct.html) and [Contributing](/contributing.html)

## Technical Strategy: Hardware as Implementation Media

SSCCS is first and foremost a software project—a compiler, a runtime, and a declarative format that allows computation to be expressed as stationary structure. It is designed to target multiple hardware backends, from conventional CPUs to emerging open-hardware platforms.

- Hardware needs a programming model. Open instruction sets provide the "what". SSCCS provides the "how"—a way to describe computation as geometric structure and automatically map it to the underlying hardware through a dedicated compiler.
- Verifiability is a requirement, not a luxury. As safety-critical systems grow, demand for deterministic computation increases. SSCCS offers verifiability by design, built into its core semantics.
- Energy efficiency is a first-order constraint. Data movement is the dominant energy sink. By eliminating it through structural isolation, SSCCS addresses physical limits facing chip designers—without requiring hardware changes.

In the current landscape—driven by agentic AI and HPC—SSCCS solves:

1. Deterministic latency for safety-critical applications.
2. The von Neumann bottleneck, bypassing data-movement costs through software-driven structural mapping.

### Target Platforms for Validation

To transition from pure-software simulation to tangible hardware validation, we will target specific open-hardware platforms with broad community adoption. These will serve as demonstration targets for our compiler and runtime, not as the primary development environment.

- CVA6 (OpenHW Group): Target for "Safe" dual-core lock-step components, aligning with our verifiability goals. Our compiler will emit code that leverages its safety features.
- CORE-V Wally: An academic 5-stage pipeline ideal for validating structural mapping concepts. We will use it to measure the impact of our compiler optimisations.
- Vector and Graph Extensions: Leveraging RISC-V Vector (RVV) to demonstrate energy-per-op gains for graph-like computations inherent in our model.

### Key Architectural Decision

Develop a target-agnostic execution interface (HAL) within the codebase. This layer will abstract the underlying execution engine, allowing the core SSCCS logic (parser, analyser, layout resolver) to remain unchanged while swapping the backend between:

- The current pure simulator.
- A future RISC-V custom instruction dispatcher (via inline assembly or C FFI).
- FPGA-accelerated co-processors.

This ensures that the ontological core requires zero rewrites when porting to physical silicon, keeping the project fundamentally a software initiative.

## Open Format and Ecosystem Integration

The global technology landscape is changing. The rise of open instruction set architectures (ISAs) has fundamentally altered how new computing ideas can be realised. Unlike proprietary architectures, open ISAs offer:

- Full transparency: specifications are open, and implementations can be freely studied, modified, and extended.
- A rapidly growing ecosystem: from academic research groups to industry consortia, a vibrant community is actively building the next generation of processors.
- Tangible, concrete targets: real silicon and FPGA platforms exist today, allowing experimental computing models to be tested on actual hardware.

This shift creates an unprecedented opportunity. Instead of spending months on paperwork to ask for support, we can now directly engage with the ecosystem where new hardware is being built. In this context, our goal is no longer to secure abstract "funding" but to become a visible contributor to a living technological movement—through software that makes hardware easier to program.

Hardware platforms are not the focus of SSCCS; they are the natural implementation media for the structural observation model. The open .ss format is the language layer through which logical design dictates physical implementation. Hardware provides the substrate; SSCCS provides the grammar.

## Documentation-First Infrastructure and Self-Evolving Knowledge Base

Our Documentation-First philosophy represents a fundamental shift in how we build software in the era of agentic development. We treat accumulated knowledge not as an afterthought, but as primary infrastructure. Our infrastructure is designed as an Observable Knowledge Graph (OKG)—a structured, machine-readable corpus optimized for LLM/RAG integration. Every output follows deterministic paths and adheres to C2PA provenance standards.

By capturing every concept, design decision, and implementation detail in a structured, provenance-tracked form, we enable AI systems to explore, reason about, and extend the underlying computational paradigm. This creates a platform for emergent discovery, where AI agents can identify connections and opportunities that human researchers might overlook.

Consequently, the documentation system is not merely a publishing tool; it is a core technical artifact. It serves as the foundation for knowledge management, AI integration, and public communication. It is the engine of radical, self-accelerating project growth. Documentation is the interface between human intent and machine reasoning. It ensures that the project grows not just through code, but through verifiable, shared understanding.

See the [Documentation Home](/index.html) for technical details.

## Immediate Action Plan

### Technical Integration (Cross-Regional)

- Maintain software-first development: Continue refining the compiler, runtime, and open format. Keep the codebase clean and modular.
- Select concrete open-hardware platforms for validation: Target CVA6, CORE-V Wally, and Vector extensions as demonstration backends.
- Port SSCCS concepts to these platforms:
  - Phase 1: Define structural mapping as custom instructions or co-processor extensions via simulation (QEMU or custom emulator).
  - Phase 2: Move to FPGA prototypes running real examples (vector addition, graph algorithms) to validate performance and energy claims.
- Prioritise Scope: Focus strictly on one primary target initially to ensure delivery within 6-9 months, mitigating resource risks.
- Publish open-source tools: Release the stack with clear documentation. A working demonstration on FPGA carries more weight than extensive whitepapers.

### Community Engagement (Regional Focus)

- In Asia-Pacific: Engage forums with working prototypes. Highlight rapid "concept-to-silicon" potential and the ease of integrating our software stack with their hardware.
- In Europe: Share formal specifications with verification groups for deep technical exchange. Our codebase is well-suited for formal reasoning.
- In North America: Connect with foundations emphasising native integration benefits. Emphasise that our software is ready to be adopted by hardware projects.
- In the Middle East: Initiate outreach to key innovation hubs for joint research tracks, offering to adapt our software to their hardware needs.

### Partnership Without Dependency

- We seek collaborators, not sponsors: Identify groups active in open-hardware interested in novel programming models.
- We offer technology, not a request: We are developing a new way to program open hardware. Our software stack is already functional on simulation; we are looking for partners to help validate it on real silicon.
- Organic Evolution: Let partnerships grow from technical alignment, not application forms.

### Licensing Compatibility

Our code is licensed under Apache 2.0, aligning perfectly with open-hardware norms (Solderpad/Apache). This removes legal friction, making it easier for hardware projects to integrate SSCCS components without compatibility concerns.

### Resource Sustainability

Recognising the need to fund the transition to FPGA validation:

- Micro-Grants and Bounties: Pursue targeted grants for specific milestones (for example, completing the CVA6 backend).
- In-Kind Support: Prioritise partnerships offering FPGA cloud access or engineering time.
- Lean Operations: Maintain a lean model to bridge the initial prototyping phase independently.

## Long-Term Vision and Success Metrics

The goal: Establish a new computational foundation where structure is the primitive, expressed through open-source software and eventually adopted by hardware designers.

- Short term (0-12 months): Demonstrate a working prototype on open hardware, with our software stack running on a real FPGA.
  - Success Metric: A merged Pull Request into a major open-hardware repo, independent teams running our simulator, and one joint technical paper.
- Medium term (1-3 years): Expand to complex AI/graph workloads, demonstrating measurable efficiency gains compared to traditional software stacks on the same hardware.
- Long term (3+ years): Contribute to standardisation (for example, RISC-V extensions, open format specifications), providing clear specs and reference implementations for global adoption.

Success is measured by adoption, not grant size. If future core designers consider "structural observation" natural, and software developers reach for defining scheme-segment to describe computational structure, we succeed.

## Conclusion

SSCCS is at its core a technological project. Its value lies not in the number of proposals submitted, but in the quality of its ideas and the clarity with which they are demonstrated.

The paradigm shift is clear: computation is not execution over time; it is the collapse of structured potential under observation. Loops disappear into layout. Data is the shadow cast by collapsed possibility. Time is one coordinate among many. The compiler maps structure to topology. The runtime observes and projects.

The current global momentum around open instruction set architectures offers a unique opportunity to embed SSCCS into a living ecosystem where new hardware is being built. By focusing on direct technical engagement with hardware designers and system builders, we turn the project's strength—its foundational nature—into its primary asset.

We will approach each region with respect, seeking win-win relationships with partners willing to engage seriously with our nascent idea. The immediate goal is no longer to write another proposal, but to produce a tangible, open-source artifact that the community can see, run, and build upon.

### Next Steps for Prospective Collaborators

1. Read: Start with the Whitepaper to understand the structural observation model.
2. Explore: Browse the GitHub repository and run the simulator locally.
3. Engage: Join our technical forum with a concrete question, proposal, or prototype idea.
4. Contribute: Submit a PR, open an issue, or propose a joint validation target.

---

© 2026 [SSCCS Foundation](https://ssccs.org) — Open-source computing systems initiative building a computing model, software compiler infrastructure, and open hardware architecture.

- Whitepaper: [PDF](https://ssccs.org/wp) / [HTML](https://ssccs.org/wpw) DOI: [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg). Authenticated via GPG: [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99). Licensed under *Apache 2.0*. 
- Governed by the [Foundational Charter and Statute](https://ssccs.org/legal) of the SSCCS Foundation (in formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial review; full intellectual responsibility with author(s). All major outputs are [C2PA-certified](https://ssccs.org/wpc2pa).