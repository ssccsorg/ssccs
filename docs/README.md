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
observation-driven computing model that challenges the current
decades-old paradigm by redefining computation as the projection of
static potential under dynamic constraints, rather than sequential
instruction sequencing, state mutations, and data movement between
memory and processor. This model treats time as merely one axis of
multi-dimensional computation rather than an absolute sequence,
employing a Geometric Manifold to ensure lossless interpretation and
provide inherent structural isolation against interference.

For the full philosophical foundation and technical specification, see
the Whitepaper [PDF](https://ssccs.org/wp)
[HTML](https://ssccs.org/wpw).

## Getting Started

### 1. Clone the Repository

``` bash
git clone https://github.com/ssccsorg/ssccs.git
cd ssccs
```

### 2. Explore the Proof of Concept

The Rust PoC demonstrates the core ontological layers. See
[poc/README.md](poc/README.md) for detailed build and run instructions.

``` bash
cd poc
cargo build --release
cargo run --release
```

### 3. Generate the Whitepaper

The whitepaper (PDF, HTML, GFM) is built with Quarto and signed with
C2PA. A convenient build script is provided:

``` bash
cd docs
python build.py whitepaper
```

To build all artifacts (whitepaper and C2PA manifest) in one step:

``` bash
cd docs
python build.py          # default target 'all'
```

See [docs/whitepaper/README.md](docs/whitepaper/README.md) for full
prerequisites and advanced rendering options.

## Community & Collaboration

SSCCS is developed as a public‑good, community‑driven project. We
welcome contributions from researchers, engineers, legal experts, and
enthusiasts.

- Official Website: <https://ssccs.org>
- GitHub Repository: <https://github.com/ssccsorg>
- Discussion Forum: [GitHub
  Discussions](https://github.com/ssccsorg/ssccs/discussions)
- Whitepaper (PDF): <https://ssccs.org/wp> (C2PA‑authenticated)
- Legal Charter: <https://ssccs.org/legal>

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

© 2026 SSCCS Foundation — A non-profit research initiative, formalized
through global standards and substantiated by its cryptographic
authenticity.

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
