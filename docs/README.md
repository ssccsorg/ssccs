# Schema–Segment Composition Computing System (SSCCS)

SSCCS (Schema–Segment Composition Computing System) is an
observation-driven computing model that defines deterministic
computation as the realization of structured potential under dynamic
constraints. In an era of increasing complexity and distributed systems,
this contrasts with the traditional von Neumann approach of instruction
sequencing, state mutations, and data movement between memory and
processor, and the compiler’s role shifts from translating code to
optimizing the topology of data movement. This model treats time as
merely one axis of multi-dimensional computation rather than an absolute
sequence, with inherent structural isolation against interference and
lossless interpretation via a Geometric Manifold.

For the full philosophical foundation and technical specification, see
the Whitepaper [PDF](https://ssccs.org/wp)
[HTML](https://ssccs.org/wpw).

## Proof of Concept

The Rust PoC demonstrates the core ontological layers. See
[poc/README.md](/poc/README.md) for detailed build and run instructions.

``` bash
git clone https://github.com/ssccsorg/ssccs.git
cd ssccs
cd poc
cargo build --release
cargo run --release
```

If you use SSCCS in your research, please cite the software using the metadata provided in [CITATION.cff](/CITATION.cff).

## Community & Collaboration

SSCCS is developed as a public‑good, community‑driven project. We
welcome contributions from researchers, engineers, legal experts, and
enthusiasts.

- [Official Website](https://ssccs.org)
- [Documentation](https://docs.ssccs.org)
- [GitHub Discussions](https://github.com/ssccsorg/ssccs/discussions)
- [Deep Pair-Coding on Zed](https://zed.dev/channel/ssccsorg-37547): And support the spirit of Zed @zed-industries.
- [Legal Charter](/docs/legal/index.qmd)
- [Code of Conduct](/docs/code_of_conduct.md)
- [Contributing Guidelines](/docs/contributing.md)

## Documentation

The SSCCS documentation suite consists of several formal documents:

- **[Whitepaper](https://ssccs.org/wp)**: The core technical
  specification, available as PDF and HTML.
- **[Project Direction](/docs/direction/index.md)**: Strategic orientation and regional engagement for the SSCCS initiative.
- **[Manifesto](/docs/axioms/manifesto.qmd)**: The high‑level philosophical and
  technical introduction.
- **[Guide](/docs/axioms/guide.md)**: A comprehensive guide to SSCCS core
  concepts.
- **[Legal documents](/docs/legal/index.qmd)**: The foundation’s charter
  and statutes.
- **[Research notes](/docs/research)**: Informal technical explorations.

All major documents are authored in Quarto (`.qmd`) and can be rendered
to PDF, HTML, and Markdown using the SDBS (SSCCS Documentation Build
System). SDBS handles Quarto rendering, C2PA signing (for PDFs), and
output management with intelligent caching and parallel execution.
See the [SDBS repository](https://github.com/ssccsorg/sdbs) for setup
instructions and usage documentation.

For detailed prerequisites and advanced rendering options, see
[docs/whitepaper/README.md](/docs/whitepaper/README.md).

## Governance

The SSCCS Foundation is a open-source foundation (in formation) that holds
the intellectual property, manages the trademark, and oversees the
standardization process. The foundation’s charter ensures that the
project remains open, neutral, and aligned with its mission of creating
a verifiable, sustainable computational commons.

All technical decisions are made through open RFCs and consensus among
maintainers. The foundation’s statutes guarantee that no single
corporation or individual can control the direction of the architecture.

## Contributing

We invite contributions of all kinds:

- Code: Rust implementations, formal proofs, hardware descriptions.
- Documentation: Whitepaper improvements, tutorials, API docs.
- Research: Formal analysis, performance benchmarks, security audits.
- Outreach: Blog posts, conference talks, educational material.

Please read [contributing.md](/docs/contributing.md) for guidelines on pull requests, code style, and licensing.

## Acknowledgments

SSCCS builds upon decades of research in functional programming, formal
verification, hardware design, and cryptographic provenance. We are
grateful to the open‑source communities that have made this work
possible, and to the early collaborators who have contributed ideas,
code, and critical feedback.

The project is currently maintained by the SSCCS Foundation and a
growing network of volunteers. If you would like to support the
initiative financially or in kind, please contact <contact@ssccs.org>.

------------------------------------------------------------------------

© 2026 [SSCCS Foundation](https://ssccs.org) — Open-source computing systems initiative.

- Whitepaper: [PDF](https://ssccs.org/wp) /
  [HTML](https://ssccs.org/wpw) DOI:
  [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via
  CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg).
  Authenticated via GPG:
  [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99).
  Licensed under *Apache 2.0*.
- Governed by the [Foundational Charter and
  Statute](https://ssccs.org/legal) of the SSCCS Foundation (in
  formation).
- Provenance: Human-in-Command, AI-assisted. Aligns with [ISO/IEC JTC 1/SC 42](https://www.iso.org/committee/6794475.html) and [C2PA-certified](https://ssccs.org/wpc2pa). Full intellectual responsibility with author(s).
