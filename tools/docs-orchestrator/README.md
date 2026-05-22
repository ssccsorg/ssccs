# ssccs-docs (SDBS)

Scale-out Documentation Build System — a portable Quarto orchestration layer.

## Installation

```bash
uv tool install ./tools/docs-orchestrator
```

## Usage

```bash
# Scaffold a new docs directory
ssccs-docs init docs

# Build all targets
ssccs-docs build .

# Build with website profile (parallel)
ssccs-docs build . --website -j 4

# Validate links and citations
ssccs-docs check .

# Resolve broken paths and includes
ssccs-docs resolve .
```

## License

Apache 2.0
