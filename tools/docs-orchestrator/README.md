# SDBS

SSCCS Documentation Build System — a portable Quarto orchestration layer.

## Installation

```bash
uv tool install ./tools/docs-orchestrator
```

## Usage

```bash
# Scaffold a new docs directory
sdb init docs

# Build all targets
sdb build .

# Build with website profile (parallel)
sdb build . --website -j 4

# Validate links and citations
sdb check .

# Resolve broken paths and includes
sdb resolve .
```

## License

Apache 2.0
