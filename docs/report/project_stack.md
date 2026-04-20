# Strategic Agentic Development Stack for SSCCS

## Technical Architecture Report (Revised)

### 1. Executive Summary

This document defines the development and execution stack for the State‑Space Composition Computing System (SSCCS). The architecture is structured around a clear separation of concerns:

- **Rust** is used for all performance-critical and system-level components.
- **Python** is used for orchestration, analysis, and documentation.
- **TypeScript/JavaScript** is restricted to optional interface and edge-layer roles.

A deliberate decision has been made to eliminate LaTeX from the toolchain. Documentation is treated as a first-class, executable artifact, rather than a static output. All visual and analytical outputs are generated programmatically to ensure reproducibility, version control compatibility, and machine accessibility.

---

### 2. Core Toolchain

| Layer | Technology | Justification |
|-------|------------|----------------|
| System Core | Rust (stable) | Deterministic execution, memory safety, and direct hardware interaction |
| Orchestration | Python 3.12+ | Rapid iteration, strong ecosystem, high compatibility with LLM‑generated code |
| Build Systems | Cargo + uv | Unified, high‑performance dependency and build management |
| Interoperability | PyO3 | Safe and efficient Rust–Python integration with minimal overhead |
| Interface Layer | TypeScript (optional) | Isolated to non‑critical UI and edge communication |

The stack prioritises predictability and reproducibility over ecosystem breadth.

---

### 3. Architectural Separation

The division between Rust and Python reflects fundamentally different execution requirements:

- **Rust domain**: deterministic, latency‑sensitive, state‑critical execution
- **Python domain**: exploratory, iterative, and analysis‑driven workflows

| Function | Implementation | Rationale |
|----------|----------------|------------|
| Hardware interaction | Rust | Requires direct system access and strict control over memory and timing |
| SSCCS compilation | Rust | Core transformation must be verifiable and deterministic |
| Runtime execution | Rust | Ensures consistency across environments |
| Data analysis & experimentation | Python | Faster iteration and richer tooling |
| Documentation generation | Python | Enables executable and reproducible reporting |

This separation avoids mixing concerns and reduces systemic complexity.

---

### 4. Documentation Strategy

#### 4.1 Rationale for Removing LaTeX

LaTeX is not used due to the following limitations:

- Output is not machine‑readable
- Poor integration with version control (diffing, merging)
- High dependency overhead in containerised environments
- Limited compatibility with LLM‑driven workflows

The requirement is not typesetting quality alone, but **programmable documentation**.

#### 4.2 Visualization Stack

All figures and diagrams are generated using Python‑based tools:

| Tool | Role |
|------|------|
| Matplotlib | Core rendering engine |
| SciencePlots | Standardised academic styling |
| Schemdraw | Structural and schematic diagrams |
| Pygraphviz | Graph and state layout |
| Proplot | Multi‑panel figure management |

Outputs are generated in **SVG** (primary) and **PDF** (secondary) formats to maintain both scalability and compatibility.

#### 4.3 Quarto Integration

Quarto is used as the document execution and publishing system:

- Executes embedded Python code
- Produces HTML (primary) and PDF (secondary via Typst)
- Maintains a single source of truth (`.qmd`)

This enables:

- Full reproducibility of reports
- Direct modification by automated systems (including LLMs)
- Elimination of post‑processing steps

---

### 5. Version Control and State Management

**Git** is used as the unified storage layer for:

- Source code
- Schema definitions (`.ss`)
- Generated outputs (SVG, HTML, PDF)
- Logs and experimental data

Large artifacts are optionally stored via object storage (e.g., S3) or Git LFS.

This approach ensures:

- Complete auditability
- Deterministic reconstruction of past states
- Elimination of external database dependencies for most workflows

---

### 6. CI/CD and Deployment

The system is designed for minimal and reproducible environments.

| Component | Technology |
|-----------|------------|
| CI | GitHub Actions / Gitea |
| Containers | Docker (Alpine‑based) |
| Base Image | Rust + Python + uv |
| Optional Services | Node.js (isolated) |

**Pipeline structure:**

1. Rust validation (build, lint, test)
2. Python validation (tests, lint)
3. Documentation generation (Quarto)
4. Artifact storage or commit

No LaTeX or heavyweight runtime dependencies are included.

---

### 7. Execution Environments

| Context | Environment |
|---------|-------------|
| Development | Local (Linux/macOS/WSL2) |
| CI | Headless Linux |
| Benchmarking | Dedicated hardware |
| Production | Containerised (Rust + Python) |
| Edge Layer | Optional Node.js service |

All environments are aligned to minimise drift.

---

### 8. Role of JavaScript

JavaScript is intentionally excluded from the core system.

Its use is limited to:

- Optional visualisation frontends
- Edge‑layer request forwarding

These components are loosely coupled and do not impact the core runtime.

---

### 9. Strategic Alignment

The stack aligns with several emerging patterns:

- Increased use of pretrained time‑series models (e.g., TimesFM)
- Shift toward executable documentation systems (e.g., Quarto)
- Adoption of LaTeX‑free typesetting via Typst
- Improvements in zero‑copy interop through PyO3
- Growing use of Git as a state and artifact ledger

These trends reinforce the design choices made in this architecture.

---

### 10. Conclusion

The SSCCS stack is designed to support a system where:

- Execution must be deterministic
- Documentation must be reproducible
- Tooling must be compatible with automated agents

Rust and Python are not interchangeable in this context; they address different layers of the problem space. By enforcing this separation and removing legacy components such as LaTeX, the system remains:

- Operationally lightweight
- Structurally clear
- Adaptable to AI‑assisted development workflows
