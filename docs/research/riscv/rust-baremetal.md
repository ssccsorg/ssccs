# Rust Bare‑Metal Toolchain as a Foundation for RISC-V Integration
SSCCS Foundation
April, 2026

# Abstract

This research note examines the Rust embedded and bare‑metal programming
ecosystems as documented in the *Rust Embedded Book* and *Comprehensive
Rust: Bare‑Metal*, and maps their principles to the ongoing
hardware‑integration research of the Schema–Segment Composition
Computing System (SSCCS). SSCCS redefines computation as structural
observation, requiring custom RISC‑V instructions and a deterministic,
memory‑safe runtime. The Rust bare‑metal toolchain provides a unique
foundation for implementing SSCCS observation primitives, offering
zero‑cost abstractions, guaranteed memory safety, and seamless
integration with RISC‑V targets. We compare the SSCCS
hardware‑integration prototype against the patterns and recommendations
of the Rust embedded guides, identifying alignment points, gaps, and
opportunities for further research. The note concludes with a concrete
roadmap for using Rust’s embedded ecosystem to accelerate SSCCS
validation on OpenHW CORE‑V and other RISC‑V platforms.

# Introduction

## Motivation

The Rust programming language has emerged as a compelling choice for
embedded and bare‑metal development due to its memory‑safety guarantees,
zero‑cost abstractions, and expressive type system. Two canonical
resources—the *Rust Embedded Book* [\[1\]](#ref-rustembeddedbook) and
the *Comprehensive Rust: Bare‑Metal*
[\[2\]](#ref-comprehensiverust)—systematically present the patterns,
tooling, and mindset required to write reliable firmware and low‑level
software without a standard library.

Concurrently, the Schema–Segment Composition Computing System (SSCCS)
proposes a paradigm shift from instruction‑sequence computing to
**structural observation**, where computation emerges from the
deterministic projection of immutable Segments within a dynamic Field
[\[3\]](#ref-lee2026). Validating this model on real hardware—especially
on open‑source RISC‑V cores—demands a software stack that can generate
custom instructions, manage memory layouts without unnecessary data
movement, and provide verifiable execution traces.

This research note asks: **How can the Rust bare‑metal ecosystem
accelerate the implementation and validation of SSCCS observation
primitives on RISC‑V hardware?** We examine the recommendations of the
two Rust guides, compare them with the current SSCCS
hardware‑integration prototype, and outline a concrete development
pathway.

## Scope

We focus on the following aspects of the Rust embedded guides:

1.  **Toolchain setup** – using `rustup`, target specifications
    (`riscv32imac‑unknown‑none‑elf`), and the `cargo‑generate` workflow.
2.  **`#![no_std]` and allocation** – working without the standard
    library, leveraging `alloc` and custom heaps.
3.  **Peripheral access** – the *Peripheral Access Crate* (PAC) pattern
    and the `embedded‑hal` trait ecosystem.
4.  **Concurrency and interrupts** – critical sections, interrupt
    handlers, and the `cortex‑m‑rt` / `riscv‑rt` runtimes.
5.  **Debugging and profiling** – using `probe‑rs`, `defmt`, and
    semihosting.

We then map these topics to the SSCCS hardware‑integration research,
which currently includes a custom‑instruction emulation library, a
placeholder XIF coprocessor profile, and a test suite that runs on the
RISC‑V target.

# Summary of Rust Embedded and Bare‑Metal Guides

## Rust Embedded Book

The *Rust Embedded Book* [\[1\]](#ref-rustembeddedbook) is a
community‑driven tutorial that walks through building embedded Rust
applications step by step. Key lessons include:

- **Cross‑compilation** – adding a target with `rustup target add` and
  using `.cargo/config.toml` to set default flags.
- **Minimal runtime** – the `cortex‑m‑rt` crate provides a startup
  sequence, vector table, and a `#[entry]` macro.
- **Memory‑mapped I/O** – accessing registers via `volatile` operations
  or generated PACs.
- **Hardware abstraction layers** – the `embedded‑hal` traits (e.g.,
  `OutputPin`, `Serial`) enable portable driver code.
- **Concurrency** – using `cortex‑m`’s `Mutex` and `critical‑section` to
  share data between interrupts.
- **Debugging** – integrating `defmt` for lightweight logging and
  `probe‑rs` for flashing and live debugging.

The book emphasizes a **bottom‑up** approach: start with a minimal
`no_std` program, gradually introduce abstractions, and keep the
hardware in view at all times.

## Google’s Comprehensive Rust: Bare‑Metal Guide

The *Comprehensive Rust* bare‑metal guide (published by Google)
[\[2\]](#ref-comprehensiverust) focuses on the fundamentals of running
Rust without an operating system, covering:

- **Boot process** – the role of the linker script, the reset handler,
  and initializing `.data`/`.bss`.
- **Global allocators** – implementing a simple bump allocator to enable
  `alloc` collections.
- **Exception handling** – defining exception vectors and using the
  `#[exception]` attribute.
- **Application processors vs. microcontrollers** – differences between
  `cortex‑a` and `cortex‑m` targets.
- **Safety patterns** – using `Owned` and `Borrowed` wrappers to enforce
  peripheral ownership.

## Common Themes

Both resources underscore:

1.  **Layered abstraction** – from raw registers to type‑safe HALs.
2.  **Compile‑time guarantees** – Rust’s ownership and borrowing prevent
    data races and illegal memory access.
3.  **Toolchain integration** – seamless cooperation between `cargo`,
    `rustc`, and vendor‑specific utilities.
4.  **Community‑driven crates** – a rich ecosystem of
    `no_std`‑compatible libraries (e.g., `heapless`, `embedded‑time`).

These themes align directly with SSCCS’s need for a reliable,
verifiable, and portable low‑level software stack.

# Current SSCCS Hardware‑Integration Status

## Prototype Overview

As documented in `hardware‑integration‑notes.md`, we have established a
dedicated Rust workspace (`hardware‑integration/`) that contains:

- A `no_std` library crate (`ssccs‑hardware‑integration`) linking to the
  SSCCS PoC crates (`ssccs‑core`, `ssccs‑primitive`).
- An `instructions` module that encodes and decodes custom RISC‑V
  instructions (`custom1`/`custom2`) and provides software emulation of
  observation primitives (`OBSERVE`, `COLLAPSE`).
- A placeholder `CoreVXifProfile` that models the OpenHW CORE‑V XIF
  interface.
- Unit and integration tests that run on the host and (in the future) on
  the RISC‑V target.

The prototype successfully compiles for `riscv32imac‑unknown‑none‑elf`
and passes all six defined tests.

## Alignment with Rust Embedded Practices

| Rust Embedded Guide Recommendation | SSCCS Prototype Status |
|:---|:---|
| Use `rustup target add` to install the RISC‑V target | **Done** (`riscv32imac‑unknown‑none‑elf`) |
| Mark the crate as `#![no_std]` | **Done** (`#![no_std]` in lib.rs) |
| Provide a panic handler (e.g., `panic‑halt`) | **Done** (`panic‑halt` dependency) |
| Use a runtime crate (`riscv‑rt`) for startup | **Done** (`riscv‑rt` dependency) |
| Define custom sections in linker script | **Not yet** – linker script default |
| Implement `embedded‑hal` traits for portability | **Not yet** – HAL traits not defined |
| Use `defmt` or `log` for structured logging | **Not yet** – logging uses `println` in host tests |
| Leverage `cargo‑generate` for project templating | **Not yet** – project created manually |

## Gaps Identified

1.  **No custom linker script** – The prototype relies on the default
    linker script provided by `riscv‑rt`. For fine‑grained control over
    memory layout (e.g., placing Scheme segments in specific RAM
    regions), a custom linker script will be needed.

2.  **Missing HAL abstraction** – The `CoreVXifProfile` is a concrete
    struct, not an implementation of an `embedded‑hal` trait. Adopting
    the HAL pattern would make the SSCCS coprocessor portable across
    different RISC‑V cores.

3.  **Limited debugging infrastructure** – The prototype uses `println!`
    for host‑side tests but has no embedded‑side logging. Integrating
    `defmt` would enable lightweight, structured logging on real
    hardware.

4.  **No interrupt or exception handling** – The observation primitives
    are currently purely computational; they do not interact with
    interrupts or exception vectors. In a real system, observation
    instructions may need to be interruptible or may raise exceptions on
    invalid configurations.

5.  **Manual project setup** – The workspace was created manually. A
    `cargo‑generate` template could accelerate the creation of future
    SSCCS‑hardware experiments.

# Opportunities for Deeper Integration

## Leveraging `embedded‑hal` for SSCCS Coprocessor Abstraction

The `embedded‑hal` trait set provides a common interface for hardware
peripherals (GPIO, UART, SPI, etc.). We can define a new trait for SSCCS
observation primitives:

``` rust
pub trait ObservationCoprocessor {
    /// Issue an observation instruction, returning the projection.
    fn observe(&mut self, scheme_id: u32, field_id: u32, rule_id: u32) -> Result<u32, ObservationError>;
    
    /// Collapse multiple segments according to a mask.
    fn collapse(&mut self, scheme_id: u32, segment_mask: u32, field_id: u32) -> Result<u32, ObservationError>;
    
    /// Check whether the coprocessor is ready to accept a new observation.
    fn is_ready(&self) -> bool;
}
```

Concrete implementations could be: - `SoftwareObservation` – the current
emulation fallback. - `XifObservation` – a hardware driver for the
OpenHW CORE‑V XIF interface. - `FpgaObservation` – an accelerator mapped
to an eFPGA fabric.

This design would allow SSCCS algorithms to be written once and deployed
across simulation, FPGA, and ASIC targets.

## Custom Linker Script for Scheme Memory Layout

SSCCS Schemes define a structural mapping from coordinate space to
logical addresses. By writing a custom linker script, we can reserve
memory regions for Scheme segments, Fields, and projection buffers,
ensuring that the compiler’s layout decisions respect the spatial
relationships implied by the Scheme.

Example linker script snippet:

``` ld
MEMORY
{
    FLASH (rx) : ORIGIN = 0x00000000, LENGTH = 256K
    RAM (rwx)  : ORIGIN = 0x20000000, LENGTH = 64K
    SCHEME (r) : ORIGIN = 0x20010000, LENGTH = 32K   /* Reserved for Scheme segments */
    FIELD (rw) : ORIGIN = 0x20018000, LENGTH = 8K    /* Reserved for Field constraints */
}

SECTIONS
{
    .scheme_segments : {
        KEEP(*(.scheme_segments))
    } > SCHEME
}
```

The SSCCS compiler could then emit assembly that places segments into
`.scheme_segments`, guaranteeing that adjacent coordinates reside in
adjacent memory locations—a prerequisite for efficient observation.

## Structured Logging with `defmt`

The `defmt` (“de‑format”) framework provides a lightweight, efficient
logging mechanism that encodes log frames as integer indices,
drastically reducing the bandwidth required for debugging. Integrating
`defmt` into the hardware‑integration library would allow us to trace
observation events, Field updates, and coprocessor state changes with
minimal overhead.

``` rust
use defmt::{info, warn, error};

impl ObservationCoprocessor for XifObservation {
    fn observe(&mut self, scheme_id: u32, field_id: u32, rule_id: u32) -> Result<u32, ObservationError> {
        info!("Observing scheme={:x}, field={:x}, rule={:x}", scheme_id, field_id, rule_id);
        // … hardware interaction
        let projection = …;
        info!("Projection result={:x}", projection);
        Ok(projection)
    }
}
```

## Interrupt‑Driven Observation

In a real‑time system, observation requests may arrive from multiple
sources (sensors, network packets, other cores). Using Rust’s
`critical‑section` and `cortex‑m` (or `riscv‑rt`) interrupt facilities,
we can design an observation queue that safely accepts requests from
interrupt handlers and processes them in a low‑priority background loop.

This pattern aligns with the *Concurrency* chapter of the Embedded Book
and would demonstrate how SSCCS’s immutability primitives simplify
concurrent access (no locks needed at the logical level).

# Roadmap: Next Steps Guided by Rust Embedded Practices

Based on the analysis above, we propose the following concrete actions:

1.  **Adopt `embedded‑hal` trait design** (Month 1) – Refactor
    `CoreVXifProfile` into a trait and provide at least two
    implementations: a software emulator and a mock hardware driver.

2.  **Create a custom linker script** (Month 1) – Develop a linker
    script that reserves memory regions for Scheme segments and Fields,
    and integrate it into the crate’s build system via `build.rs`.

3.  **Integrate `defmt`** (Month 2) – Add `defmt` as a dependency,
    implement the `Format` trait for SSCCS core types, and produce a
    simple demo that logs observation sequences.

4.  **Set up `cargo‑generate` template** (Month 2) – Package the
    hardware‑integration workspace as a template so that new team
    members (or external contributors) can spin up a SSCCS‑hardware
    project with one command.

5.  **Implement interrupt‑safe observation queue** (Month 3) – Using
    `riscv‑rt`’s interrupt macros and `critical‑section`, build a
    concurrent observation scheduler that can be tested in simulation.

6.  **Port to OpenHW CORE‑V MCU DevKit** (Month 4) – With the
    abstractions in place, target the actual CORE‑V MCU hardware, using
    the `corev‑pac` crate (if available) or hand‑written register
    definitions.

Each step will be accompanied by a small example commit and a test that
verifies the new capability, following the pedagogical style of the Rust
Embedded Book.

# Additional Considerations (Optional Enhancements)

### RISC‑V‑Specific Register Access

The XIF interface may be configured via CSRs (Custom System Registers).
The `rust‑riscv` crate provides a `csr!` macro that could be used to
define and manipulate these registers safely. Incorporating this macro
would align the SSCCS coprocessor driver with established RISC‑V
bare‑metal practices.

### High‑Level Hardware Description Languages

Beyond Verilog/VHDL, eFPGA integration could leverage modern HDLs such
as **Amaranth** (Python‑based) or **SpinalHDL** (Scala‑based), which
offer stronger type safety and better integration with software
toolchains. These languages can generate FPGA bitstreams while remaining
accessible to software engineers.

### Memory Protection

SSCCS’s isolation properties could be reinforced by hardware memory
protection. RISC‑V provides PMP (Physical Memory Protection) and, in
higher‑end cores, MMU‑based virtual memory. While this is an advanced
topic that may be omitted from the initial prototype, future
safety‑critical deployments should consider integrating PMP regions to
separate Scheme segments, Fields, and projection buffers.

# Recommendations

This document presents a **realistic and actionable research plan** that
accurately identifies points where the Rust embedded ecosystem can
contribute concretely to SSCCS hardware integration. Notably, it avoids
exaggerated promises (e.g., “hardware performance numbers”, “full ASIC
implementation”) and honestly discloses current limitations.

**Recommended actions:**

1.  **Proceed with the roadmap** – implement the `embedded‑hal` trait
    and custom linker script work as outlined.
2.  **Adopt `defmt` early** – structured logging will greatly assist
    hardware debugging and should be attempted in the initial phases.
3.  **Secure OpenHW CORE‑V MCU DevKit access** – obtaining the physical
    hardware early is crucial for validating the prototype on a real
    RISC‑V target.
4.  **Prepare community contributions** – based on this research, draft
    documentation (e.g., a guide to implementing custom instructions via
    XIF) that can be contributed to the OpenHW community.

# Conclusion

The Rust embedded and bare‑metal guides provide a robust,
community‑validated foundation for building low‑level software that is
safe, portable, and maintainable. The SSCCS hardware‑integration
prototype already follows many of their recommendations—`no_std`, a
dedicated target, a panic handler, and a runtime crate—but several
opportunities for deeper alignment remain.

By adopting the `embedded‑hal` trait pattern, custom linker scripts,
`defmt` logging, and interrupt‑safe concurrency, the SSCCS research can
leverage the full power of the Rust embedded ecosystem. This will
accelerate the validation of structural observation on RISC‑V hardware,
moving the SSCCS paradigm closer to real‑world deployment.

Ultimately, the combination of Rust’s guarantees and SSCCS’s structural
model offers a promising path toward verifiable, energy‑efficient
computing—a path that the Rust embedded community is uniquely equipped
to help us walk.

# Glossary

| Term | Definition |
|----|----|
| **`no_std`** | Rust crate that does not link the standard library, enabling bare‑metal and embedded targets. |
| **PAC** | Peripheral Access Crate – a machine‑generated set of register definitions for a specific microcontroller. |
| **HAL** | Hardware Abstraction Layer – a set of traits that define portable interfaces for hardware peripherals. |
| **`defmt`** | A lightweight logging framework for embedded Rust that encodes messages as indices. |
| **Linker script** | A file that directs the linker how to place sections in memory. |
| **XIF** | CORE‑V eXtension Interface – a RISC‑V interface for tightly coupled coprocessors. |
| **Observation primitive** | A basic SSCCS operation (e.g., `OBSERVE`, `COLLAPSE`) that can be realized as a custom instruction. |

# References

<div id="refs" class="references csl-bib-body" entry-spacing="0">

<div id="ref-rustembeddedbook" class="csl-entry">

<span class="csl-left-margin">\[1\]
</span><span class="csl-right-inline">Rust Embedded Working Group, *The
embedded rust book*. 2026. Available:
<https://docs.rust-embedded.org/book/></span>

</div>

<div id="ref-comprehensiverust" class="csl-entry">

<span class="csl-left-margin">\[2\]
</span><span class="csl-right-inline">Google, “Comprehensive rust:
Bare-metal.” 2026. Available:
<https://google.github.io/comprehensive-rust/bare-metal.html></span>

</div>

<div id="ref-lee2026" class="csl-entry">

<span class="csl-left-margin">\[3\]
</span><span class="csl-right-inline">T. Lee, “Schema–segment
composition computing system whitepaper.” DOI: 10.5281/zenodo.18759106,
2026.</span>

</div>

</div>

------------------------------------------------------------------------

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research and
engineering initiative building a computing model and compiler
infrastructure.

- Whitepaper: [PDF](https://ssccs.org/wp) /
  [HTML](https://ssccs.org/wpw) DOI:
  [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via
  CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg).
  Authenticated via GPG:
  [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99).
  Licensed under *Apache 2.0*.
- Governed by the [Foundational Charter and
  Statute](https://ssccs.org/legal) of the SSCCS Foundation (in
  formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial
  review; full intellectual responsibility with author(s). All major
  outputs are [C2PA-certified](https://ssccs.org/wpc2pa).
