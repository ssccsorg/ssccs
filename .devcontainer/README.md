# SSCCS Development Environment

The DevContainer provides a complete, reproducible development environment for the entire SSCCS project. It is located at the **project root** (`.devcontainer/`), ensuring consistent tooling for documentation, Rust code, Proof-of-Concepts, and any other development work.

## Quick Start

1. Open the repository root in VS Code or supported IDE.
2. Reopen in container (`F1` → `Dev Containers: Reopen in Container`).
3. Wait for the setup script to finish (installs Quarto, Python, TinyTeX, c2patool, and system dependencies).
4. Build the documentation:

   ```bash
   cd docs
   python build.py --website
   ```

## What’s Inside (Current)

- **Base image**: Ubuntu 24.04 (x86_64) – matches GitHub Actions runner
- **Python 3.11** (via devcontainer feature)
- **Quarto 1.9.35** – for documentation rendering
- **TinyTeX** with LaTeX packages (from `docs/tex-packages.txt`)
- **c2patool 0.9.12** – for C2PA provenance signing
- **System tools**: `graphviz`, `librsvg2-bin`
- **VS Code extensions**: Quarto, Python, Pylance, Jupyter

## Future Expansion

This environment is not limited to documentation. As the project grows (e.g., Rust backends, embedded PoCs), additional tools can be added:

- Rust/Cargo (via `rustup`)
- Additional compilers or embedded toolchains
- Custom test frameworks

To extend the environment, edit `docs/Dockerfile` or `.devcontainer/post-create-command.sh` accordingly.

## Key Paths

- Workspace root = repository root
- Documentation source = `docs/`
- Build script = `docs/build.py`
- Python dependencies = installed directly in the Dockerfile via `uv pip`
- LaTeX packages = installed directly in the Dockerfile via `tlmgr`

## Notes

- The documentation build environment **exactly mirrors** the GitHub Actions workflow (`.github/workflows/deploy-docs-ghpage.yml`).
- If you modify dependencies, rebuild the container (`Rebuild Container` from the command palette).
- For Rust or other languages, consider using devcontainer features (`ghcr.io/devcontainers/features/rust:1`).

---

**Maintained by SSCCS Foundation** – For issues, open a ticket on GitHub.
