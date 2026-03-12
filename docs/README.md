# Schema–Segment Composition Computing System (SSCCS)


<!-- badges -->

[![License: Apache
2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![License: CC BY-NC-ND
4.0](https://img.shields.io/badge/License-CC_BY--NC--ND_4.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-nd/4.0/)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18759106.svg)](https://doi.org/10.5281/zenodo.18759106)
[![SSCCS
Foundation](https://img.shields.io/badge/Foundation-Non--Profit-8A2BE2.png)](https://ssccs.org/legal)

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
[poc/README.md](poc/README.md) for detailed build and run instructions.

``` bash
git clone https://github.com/ssccsorg/ssccs.git
cd ssccs
cd poc
cargo build --release
cargo run --release
```

## Community & Collaboration

SSCCS is developed as a public‑good, community‑driven project. We
welcome contributions from researchers, engineers, legal experts, and
enthusiasts.

- Official Website: <https://ssccs.org>
- GitHub Repository: <https://github.com/ssccsorg>
- Discussion Forum: [GitHub
  Discussions](https://github.com/ssccsorg/ssccs/discussions)
- Legal Charter: <https://ssccs.org/legal>

## Documentation

The SSCCS documentation suite consists of several formal documents:

- **[Whitepaper](docs/whitepaper.pdf)**: The core technical
  specification, available as PDF and HTML.
- **[Proposal](docs/proposal.pdf)**: A companion document focusing on
  practical implementation and sustainability.
- **[Manifesto](docs/MANIFESTO.md)**: The high‑level philosophical and
  technical introduction.
- **[Guide](docs/GUIDE.md)**: A comprehensive guide to SSCCS core
  concepts.
- **[Legal documents](docs/legal/legal.md)**: The foundation’s charter
  and statutes.
- **[Research notes](docs/research)**: Informal technical explorations.

All major documents are authored in Quarto (`.qmd`) and can be rendered
to PDF, HTML, and Markdown using the centralized build script
`docs/build.py`. This script handles Quarto rendering, C2PA signing (for
PDFs), and copying outputs to the appropriate locations.

For detailed prerequisites and advanced rendering options, see
[docs/whitepaper/README.md](docs/whitepaper/README.md).

## Governance

The SSCCS Foundation is a non‑profit entity (in formation) that holds
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

Please read
[CONTRIBUTING.md](https://github.com/ssccsorg/ssccs/blob/main/CONTRIBUTING.md)
(to be created) for guidelines on pull requests, code style, and
licensing.

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

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research
initiative, formalized through global standards and substantiated by its
cryptographic authenticity.

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
