# Whitepaper Generation with Quarto

This document explains how to generate the SSCCS Whitepaper (`Whitepaper.pdf` and `Whitepaper.md`) from the Quarto source file `Whitepaper.qmd`.

## Prerequisites

The Whitepaper uses advanced Quarto features that require several external tools:

1. **Quarto** – The document rendering engine.
2. **LaTeX** – For PDF generation, including the `pdfLaTeX` engine with `--shell-escape` support.
3. **Python** – For inline Python code that creates SVG logos.
4. **Graphviz** – For rendering `dot` diagrams embedded in the document.
5. **Inkscape** (optional but recommended) – For converting SVG images when using the LaTeX `svg` package.

## Installation

### macOS (using Homebrew)

If you have Homebrew installed, run the following commands:

```bash
# Install Quarto
brew install --cask quarto

# Install LaTeX distribution (MacTeX)
brew install --cask mactex

# Install Python (if not already present)
brew install python

# Install Graphviz
brew install graphviz

# Install Inkscape (optional, but needed for SVG inclusion in PDF)
brew install --cask inkscape
```

After installing MacTeX, ensure the LaTeX binaries are in your `PATH`. You may need to open a new terminal or run:

```bash
export PATH="/Library/TeX/texbin:$PATH"
```

### Linux (Debian/Ubuntu)

```bash
# Install Quarto
# Download the latest .deb from https://quarto.org/docs/download/
# or use the install script:
curl -LO https://quarto.org/download/latest/quarto-linux-amd64.deb
sudo dpkg -i quarto-linux-amd64.deb

# Install LaTeX (TeX Live)
sudo apt-get update
sudo apt-get install texlive-full

# Install Python (usually pre-installed)
sudo apt-get install python3

# Install Graphviz
sudo apt-get install graphviz

# Install Inkscape
sudo apt-get install inkscape
```

### Windows

Download and install:

- Quarto from [quarto.org](https://quarto.org/docs/download/)
- MiKTeX or TeX Live for LaTeX
- Python from [python.org](https://www.python.org/downloads/)
- Graphviz from [graphviz.org](https://graphviz.org/download/)
- Inkscape from [inkscape.org](https://inkscape.org/release/)

Add the installation directories to your system PATH.

## Generating the Whitepaper

Once all prerequisites are satisfied, navigate to the `docs` directory and run Quarto:

```bash
cd /path/to/qs-core/docs
```

### Render PDF

To produce the PDF version (requires LaTeX):

```bash
quarto render Whitepaper.qmd --to pdf
```

The output will be `Whitepaper.pdf`. The first run may take several minutes because LaTeX must install missing packages and compile the document.

### Render Markdown (GitHub‑Flavored Markdown)

To generate the plain‑markdown version (without LaTeX dependencies):

```bash
quarto render Whitepaper.qmd --to gfm
```

The output will be `Whitepaper.md`. This version includes the DOI badge and all diagrams as embedded SVG images (if Graphviz is available).

### Render both formats at once

```bash
quarto render Whitepaper.qmd
```

By default Quarto will produce all output formats declared in the document’s YAML header (here `gfm` and `pdf`).

## Document Structure

- `Whitepaper.qmd` – The source file containing the complete paper in Quarto Markdown.
- `Whitepaper_files/` – Directory created during rendering that holds generated SVG images and other auxiliary files.
- `_extensions/` – Contains Quarto extensions (currently only a custom extension for inline SVG).
- `Whitepaper.pdf` – The final PDF (already included in the repository).
- `Whitepaper.md` – The final Markdown version (already included in the repository).

## Troubleshooting

### LaTeX errors about missing packages

The document uses several LaTeX packages (`authblk`, `svg`, `unicode‑math`, `graphicx`, `adjustbox`). If you encounter missing‑package errors, ensure you have a **full** LaTeX installation (e.g., `texlive‑full` on Linux, or the complete MacTeX bundle). You can also manually install missing packages with `tlmgr`.

### `--shell-escape` requirement

The PDF engine is called with the `-shell‑escape` flag (enabled via `pdf‑engine‑opts: ["-shell‑escape"]`). This is necessary for the `svg` package to call Inkscape. If your LaTeX installation blocks shell‑escape for security reasons, you may need to adjust your LaTeX configuration or run Quarto in a trusted environment.

### SVG images not appearing in PDF

If the CERN and other logos are missing in the PDF, verify that:

1. Inkscape is installed and the `inkscape` command is available in your `PATH`.
2. The `svg` LaTeX package is installed (it is part of most modern LaTeX distributions).
3. The `Whitepaper_files` directory is writable and contains the generated `image0.svg` and `image1.svg` files after rendering.

### Graphviz diagrams not rendered

Ensure that the `dot` command (part of Graphviz) is in your `PATH`. Quarto will call `dot` to produce SVG diagrams; if `dot` is missing, the diagrams will be omitted.

### Python code block errors

The Python block is marked `eval: false`, so it is not executed during rendering. It only writes static SVG code into the `Whitepaper_files` folder. If you encounter Python‑related errors, make sure Python is installed and the `os` and `tempfile` modules are available (they are part of the standard library).

## Updating the Whitepaper

To modify the Whitepaper, edit `Whitepaper.qmd` and then re‑run the `quarto render` commands above. Always commit both the source `.qmd` and the rendered `.pdf`/`.md` files to the repository.

## License

The Whitepaper text is licensed under CC BY‑NC‑ND 4.0. The build instructions in this README are provided under the same license as the rest of the SSCCS project (Apache‑2.0 for code, CC BY‑NC‑ND 4.0 for documentation).

## References

- [Quarto documentation](https://quarto.org/docs/)
- [LaTeX Project](https://www.latex-project.org/)
- [Graphviz](https://graphviz.org/)
- [Inkscape](https://inkscape.org/)