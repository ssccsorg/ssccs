# Project Direction 

## Toward a New Computational Paradigm

For decades, computation has followed the von Neumann model: data and instructions stored in memory, fetched sequentially, executed by a processor, results written back. Most energy and time are spent moving data – the well‑known *data‑movement wall*.

We reimagine computation not as a sequence of steps, but as the geometry of stationary structure. In current computing, a fixed runtime logic or algorithm operates on fluid data, producing changing state. In SSCCS, the fixed geometric structure of pre-compiled data(or whatever we call it in the future.) itself is projected through observation, and the result is a deterministic state where the boundary between data and program disappears. Computation becomes structural observation, not procedural execution. (For foundational concepts, see [Guide](/guide.html), [Whitepaper](/whitepaper/whitepaper.html), [Public Proposal](/proposal/proposal.html).)

This document outlines the **highest‑level direction** – our cultural bedrock, strategic posture, and long‑horizon vision. Detailed technical roadmaps, platform‑specific plans, and measurable milestones belong to separate reports and proposals.



## Cultural Foundations

SSCCS is a software‑first initiative. We seek technical collaborators, not sponsors. Our culture prioritises reproducible results, verifiable processes, and open contribution.

### Human Comes First
Every tool, from AI to automation, is meant to serve the project and its people. Any process that inflicts unnecessary stress or alienation is a failure. Our technology should not exist at the expense of humanity; it must improve our lives and even act as a tool of resistance against everything that threatens human well-being. We will.

### Results‑Oriented Pragmatism
Code quality, maintainability, and system impact matter more than *how* the code was written. We bypass bureaucracy and exhausting debates. Discussions focus on engineering, architecture, and performance.

### Clarity of Responsibility
In 2026, AI use is as standard as a compiler. We do not mandate disclosure—only evaluate correctness, security, and test compliance. We encourage its use if it supports our project's healthy growth. Every contributor bears full responsibility for their work. Tools are aids; the human engineer remains accountable.

### Beyond Boundaries
We acknowledge that even our platforms operate within centralised constraints. Where possible, we choose open, decentralised alternatives. We encourage bold ideas that challenge conventional computing – provided they do not block others.

These principles are complementary. Rigorous technical debate is welcome; personal pressure is not.
See [Code of Conduct](/code_of_conduct.html).



## Partnership, Collaboration, and Support

SSCCS does not await institutional validation. We engage with academia, industry, open‑hardware communities, and independent researchers – guided by technical merit and reciprocal contribution.

Conventional funding mechanisms are optimised for predictability: mature toolchains, commercial consortia, incremental advances. SSCCS reimagines the substrate of computation itself. It is inherently too early‑stage and too disruptive for most existing templates.

Rather than retrofitting our work to fit funding forms, we prioritise collaboration grounded in technical substance and long‑term vision. Our engagement follows three principles:

- **Reciprocal value** – partnerships must benefit all parties.
- **Foundational over immediate** – market fit is secondary to redefining computation.
- **Substance over ceremony** – we welcome rigorous scrutiny, but only where there is genuine commitment to paradigm‑shifting work.

Where funding is needed, we treat it as a catalyst, not a goal. Our priority is tangible progress and substantive research over administrative complexity.

We are building a computational commons open to everyone. Those who share this vision are invited to join.
For collaboration details, see [Code of Conduct](/code_of_conduct.html) and [Contributing](/contributing.html).



## Technical Strategy

SSCCS is first a **software project** – a compiler, a runtime, and a declarative format that expresses computation as stationary structure. It is designed to target multiple hardware backends, from conventional CPUs to emerging open platforms.

- **Hardware needs a programming model.** Open instruction sets provide the “what”. SSCCS provides the “how” – a way to describe computation as geometric structure and automatically map it to hardware.
- **Verifiability by design** is built into our core semantics, addressing the growing demand for deterministic computation in safety‑critical systems.
- **Energy efficiency** is a first‑order constraint. By eliminating data movement through structural isolation, SSCCS addresses physical limits without requiring hardware changes.

In the current landscape – agentic AI, HPC, edge computing – SSCCS offers:
1. Deterministic latency for safety‑critical applications.
2. Bypassing the von Neumann bottleneck via software‑driven structural mapping.

### Validation on Open Hardware

To move from pure‑software simulation to tangible hardware validation, we will target **representative open platforms** – e.g., RISC‑V cores with safety features and vector extensions (including emerging platforms like NASA’s HPSC). The exact platform choices will be finalised in technical addenda, prioritising broad community adoption and alignment with our verifiability goals.

### Key Architectural Decision

We are developing a **target‑agnostic execution interface (HAL)** within the codebase. This layer abstracts the underlying engine, allowing the core SSCCS logic (parser, analyser, layout resolver) to remain unchanged while swapping backends (simulator, custom instruction dispatcher, FPGA accelerator).

Thus, the ontological core requires zero rewrites when porting to physical silicon – keeping the project fundamentally a software initiative.

### Open Format and Ecosystem Integration

The rise of open instruction set architectures (ISAs) has fundamentally changed how new computing ideas can be realised. Open ISAs offer transparency, a growing ecosystem, and tangible, real‑world targets (FPGAs, silicon).

SSCCS contributes an **open `.ss` format** – a language layer through which logical design dictates physical implementation. Hardware provides the substrate; SSCCS provides the grammar. Our goal is to become a visible contributor to a living technological movement, through software that makes hardware easier to program.



## Documentation‑First Infrastructure and Self‑Evolving Knowledge Base

Our **Documentation‑First** philosophy treats accumulated knowledge as primary infrastructure. We build an Observable Knowledge Graph (OKG) – a structured, machine‑readable corpus optimised for LLM/RAG integration. Every output follows deterministic paths and adheres to provenance standards (e.g., C2PA).

By capturing every concept, design decision, and implementation detail in a structured, provenance‑tracked form, we enable AI systems to explore, reason about, and extend the underlying paradigm. This creates a platform for emergent discovery, where AI agents can identify connections that human researchers might overlook.

The documentation system is not merely a publishing tool – it is a core technical artifact, the interface between human intent and machine reasoning. See [Documentation Home](/index.html) for details.



## Immediate Action Plan (High‑Level)

Our near‑term focus is **tangible, open‑source artifacts** that the community can run and build upon. Detailed milestones, timelines, and resource allocations are maintained in separate technical roadmaps and proposal documents.

- **Software‑first development** – Continue refining the compiler, runtime, and open format. Keep the codebase modular and clean.
- **Select open‑hardware targets** – Choose one or more RISC‑V platforms (e.g., with safety and vector capabilities) for initial validation. The final selection will balance community adoption, verifiability, and resource constraints.
- **Iterative prototyping** – Move from simulation to FPGA prototypes, demonstrating the model on real examples (e.g., vector addition, graph algorithms).
- **Publish open‑source tools** – Release the full stack with clear documentation. A working demonstration carries more weight than extensive whitepapers.

### Community Engagement (Regional)

We will engage with open‑hardware ecosystems across regions – Asia‑Pacific, Europe, North America, the Middle East – adapting our message to local interests (rapid prototyping, formal verification, integration with existing foundations, joint research tracks). Each engagement will be guided by technical substance and mutual benefit.

### Partnership Without Dependency

We seek collaborators, not patrons. We offer a novel way to program open hardware – a software stack already functional in simulation. We look for partners to help validate it on real silicon. Partnerships will grow organically from technical alignment, not application forms.

### Licensing Compatibility

Our code is licensed under **Apache 2.0**, aligning with open‑hardware norms (Solderpad/Apache). This removes legal friction, making integration easier. (For the whitepaper and certain content, a CC BY‑NC‑ND license is used – this will be reviewed for long‑term ecosystem compatibility as the project matures.)

### Resource Sustainability

We will pursue **micro‑grants and bounties** for specific milestones, prioritise **in‑kind support** (FPGA cloud access, engineering time), and maintain a **lean operational model** to bridge initial prototyping independently.



## Long‑Term Vision and Success Metrics

**Goal:** Establish a new computational foundation where *structure* is the primitive, expressed through open‑source software and eventually adopted by hardware designers.

- **Short term** – A working prototype on open hardware, with independent teams running our simulator and at least one joint technical publication.
- **Medium term** – Demonstrate measurable efficiency gains on AI/graph workloads compared to traditional stacks on the same hardware.
- **Long term** – Contribute to standardisation (e.g., RISC‑V extensions, open format specifications) with reference implementations for global adoption.

Success is measured by **adoption**, not grant size. If future core designers consider “structural observation” natural, and developers reach for the open format to describe computational structure – we succeed.



## Conclusion

The global momentum around open instruction set architectures offers a unique opportunity to embed SSCCS into a living ecosystem where new hardware is being built. By focusing on direct technical engagement with hardware designers and system builders, we turn our foundational nature into our primary asset.

We will approach each region with respect, seeking win‑win relationships with partners willing to engage seriously with our nascent idea. The immediate goal is not to write another proposal, but to produce a tangible, open‑source artifact that the community can see, run, and build upon.
