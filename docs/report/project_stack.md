# Strategic Agentic Development Stack for SSCCS

## 1. Executive Summary

This document defines the **development and execution environment** for the SSCCS (State‑Space Composition Computing System) project. The stack is designed around three core principles:

- **Rust** for the system core – memory safety, deterministic performance, low‑level hardware communication.
- **Python** for orchestration, documentation, and AI‑friendly scripting – replacing traditional shell scripts and legacy LaTeX workflows.
- **JavaScript/TypeScript** as a minimal auxiliary layer – used only for web rendering and lightweight edge‑agent services.

The strategic shift away from LaTeX is deliberate. PDF is a legacy output paradigm; the AI era demands **programmatically accessible, version‑controlled, and LLM‑friendly** documentation. By centralising all visual assets within the **Matplotlib** backend, we achieve academic‑grade output without the fragility and bloat of a full TeX distribution.

---

## 2. Core Language & Toolchain

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **System Core** | Rust (stable) | Compiler, runtime, FFI. Zero‑cost abstractions, no garbage collector, perfect for hardware‑near code. |
| **Orchestration / Scripting** | Python 3.12+ | Fast prototyping, data analysis, LLM integration, and calling Rust core via PyO3. |
| **Build & Package Management** | Cargo (Rust) + `uv` (Python) | `uv` is 10–100x faster than `pip` and replaces the entire Python packaging toolchain (pip, pip‑tools, poetry, pyenv, twine, virtualenv). |
| **Rust⇄Python Interop** | PyO3 | Zero‑overhead, safe bindings. Recent zero‑copy optimisations are critical for passing large arrays (e.g., time‑series projections) between the two languages. |
| **Auxiliary Web / Edge** | TypeScript + Node.js | Not part of the core runtime. Used only for optional web dashboards and lightweight edge‑agent adapters. |

---

## 3. Strategic Choice: Rust for Core, Python for Everything Else

The separation is not arbitrary. It reflects the fundamental difference between **system programming** (deterministic, memory‑safe, low‑level) and **agentic orchestration** (dynamic, AI‑interactive, exploratory).

| Domain | Implementation | Reason |
|--------|----------------|--------|
| Hardware communication (X11, Xvfb, memory mapping) | Rust | Direct FFI, no interpreter overhead, predictable latency. |
| SSCCS compiler (`.ss` → memory layout) | Rust | Performance and safety critical. |
| Observation runtime | Rust | Must run deterministically, often in headless or embedded environments. |
| Field logic, data analysis, experimentation | Python | LLMs produce correct Python with high probability; rapid iteration; rich scientific stack. |
| Documentation, diagram generation, reporting | Python + Quarto | Python’s lightweight, pre‑compiled‑free nature is ideal for CI/CD. |
| Shell‑script replacement | Python (with `uv` run) | Cross‑platform, typed, testable – no more bash scripts. |

**What about Julia?**  
Julia’s execution speed is attractive, but its package setup and precompilation step are heavily local‑dev oriented. For a project that must run in clean CI containers and be easily reproducible, Python + `uv` provides a much smoother experience.

---

## 4. Documentation & Reporting: The Pythonic Visualization Stack

### 4.1 Why LaTeX‑less?

LaTeX was designed for static print output. In an AI‑driven development environment:

- **PDF is a dead end** – it is not machine‑readable, not version‑diffable, and cannot be directly fed back into an LLM.
- **Full TeX distributions are bloated** – they add hundreds of megabytes to Docker images and slow down CI.
- **TikZ diagrams are code‑heavy but not agent‑friendly** – an LLM can generate Python/Matplotlib code much more reliably than raw TikZ.

### 4.2 The Matplotlib‑Centric Stack

All visual assets are generated via Python code that uses **Matplotlib** as the backend. This ensures that every chart, diagram, and schematic remains **programmatically accessible** and can be recreated on any platform without LaTeX.

| Library | Purpose |
|---------|---------|
| **Matplotlib** (engine) | Primary rendering engine; headless backends (Agg, Cairo) for CI/CD. |
| **SciencePlots** | One‑line academic styles (IEEE, Nature, Science). Gives the “LaTeX look” without LaTeX. |
| **Schemdraw** | TikZ replacement for block diagrams and circuit schematics. Uses coordinate‑and‑anchor system, renders via Matplotlib. |
| **Proplot** | Simplifies complex multi‑panel figures; automates label alignment and colorbar placement. |
| **Pygraphviz** | Interfaces with Graphviz to automatically lay out graphs, state machines, and decision trees. |

All outputs are **vector‑first** – SVG for web (Quarto HTML) and PDF for print. Both formats are fully scalable and can be inspected by automated tools.

### 4.3 Publishing with Quarto

**Quarto 1.9** is the orchestrator. It executes Python code blocks, captures Matplotlib outputs, and produces:

- **HTML** with embedded SVG – ideal for internal dashboards and LLM consumption (Quarto can generate `llms.txt` files).
- **PDF** via Typst (LaTeX‑free) – for traditional academic submission when required.

**Key advantage:** The same `.qmd` source file contains both narrative text and executable code. An LLM can read, modify, and rerun the entire document – something impossible with a binary PDF.

### 4.4 Fonts and Mathematics

- **Mathtext** (Matplotlib’s internal math renderer) uses Computer Modern fonts.  
- **`rcParams['text.usetex'] = False`** – no LaTeX installation needed.  
- Mathematical expressions are rendered identically to LaTeX, but the process is lightweight and deterministic.

---

## 5. Version Control & State Store

- **Primary VCS:** Git (GitHub / Gitea / self‑hosted)  
- **State store for all project artifacts:** Git + object storage (S3 for large blobs).  
- **What is stored in Git?**  
  - Source code (Rust, Python, TypeScript)  
  - `.ss` schemas (plain text)  
  - Generated reports (HTML, PDF, SVG)  
  - Benchmark results, logs, and observation histories (JSONL, Parquet)  
  - Compiled memory layouts (binary, optionally Git LFS)  

**Why Git as a unified state store?**  
Every project output is versioned, auditable, and replicable. For small‑to‑medium agentic teams, this eliminates the need for a separate database. The entire history of every observation, every diagram, and every report is captured in a single, distributed system.

---

## 6. CI/CD & Containerisation

| Component | Technology | Purpose |
|-----------|------------|---------|
| CI platform | GitHub Actions / Gitea Actions | Lint, test, build on every push. |
| Containerisation | Docker (Alpine base) | Lightweight, reproducible execution. |
| Base image | `rust:alpine` + Python + `uv` | <500 MB. No LaTeX, no Node.js bloat. |
| Edge‑agent image | `node:alpine` | <200 MB, only if JS service is needed. |
| Artifact caching | `uv cache`, `cargo cache` | Speed up dependency fetching. |
| Release automation | `cargo release` + `uv publish` | Tag, build, push to crates.io / PyPI. |

**CI pipeline steps:**

1. `cargo check`, `cargo test`, `cargo clippy`, `cargo fmt`
2. `uv run pytest`, `uv run ruff check`
3. `quarto render docs/` (generates HTML and PDF reports)
4. (Optional) `npm run build` for web frontend
5. Commit generated reports back to Git (or upload as CI artifacts)

---

## 7. Execution Environments

| Scenario | Environment | Notes |
|----------|-------------|-------|
| Local development | Linux/macOS/WSL2 | Rust + Python + uv + Docker + (optional) Node.js |
| CI testing | Ubuntu latest (headless) | Same as dev, but uses Xvfb if GUI simulation is needed. |
| Benchmarking | Dedicated bare‑metal / cloud instance | Isolated, reproducible hardware. |
| Production deployment | Docker container (Alpine) | Single binary (Rust) + Python runtime. |
| Edge agent | Separate Node.js container | For lightweight REST adapters; does not run core SSCCS logic. |

---

## 8. The Role of JavaScript/TypeScript

JavaScript is **not** part of the core stack. It is used only as an **auxiliary medium** for two specific purposes:

- **Web‑based visualisation dashboard** – a React/Vue frontend that consumes SSCCS projection data via REST/WebSocket. This is entirely optional.
- **Edge‑computing agent service** – a lightweight Node.js service that receives `observe` requests from constrained devices and forwards them to the main Rust+Python backend.

These components are developed and deployed separately. They do not affect the core build, test, or documentation pipeline.

---

## 9. Emerging Trends & Strategic Inspirations (2025–2026)

| Trend / Technology | Relevance to SSCCS Stack |
|--------------------|---------------------------|
| **TimesFM (Google Research)** | A pre‑trained time‑series foundation model with 200M parameters, 16k context length, and continuous quantile forecasting. Inspires the **static context + dynamic observation** pattern used in SSCCS benchmarking. |
| **LLM‑friendly Quarto output** | Quarto 1.9 can generate `llms.txt` files, making the entire documentation directly accessible to LLMs. Aligns perfectly with the goal of AI‑assisted development. |
| **Typst PDF generation** | A LaTeX‑free typesetting system that produces high‑quality PDFs. Quarto’s Typst integration allows us to drop LaTeX entirely. |
| **Zero‑copy FFI (PyO3)** | Recent optimisations eliminate memory copies when passing large arrays between Rust and Python – critical for real‑time observation pipelines. |
| **Git as a unified state store** | Increasingly adopted by agentic systems (e.g., Gitea, GitHub Copilot Workspace). Simplifies auditability and distribution. |
| **Edge AI agents with Node.js** | Lightweight JS runtimes are becoming the standard for edge adapters, while heavy computation stays in Rust/Python. |

---

## 10. Conclusion: A Future‑Proof Agentic Stack

The SSCCS project stack is not an arbitrary collection of tools. It is a **strategic response** to the demands of AI‑driven, hardware‑near, and documentation‑heavy development:

- **Rust** gives us the performance and safety required for a novel computing paradigm (state‑space composition).
- **Python** gives us the agility to explore, document, and orchestrate – with a visualization stack that finally kills LaTeX.
- **Quarto + Matplotlib** produces academic‑grade reports that are both machine‑readable and human‑readable.
- **Git** serves as the single source of truth for code, data, and every generated artifact.

This stack is lean, reproducible, and ready for the era where **LLMs are active participants in the development process**. It avoids legacy bloat (full TeX, Node.js `node_modules`, pip dependency hell) and focuses on what matters: **building, observing, and documenting the behaviour of a state‑space computer**.
