# Whitepaper Generation with Quarto

This document explains how to generate the SSCCS Whitepaper (`Whitepaper.pdf` and `Whitepaper.md`) from the Quarto source file `Whitepaper.qmd`.

## Prerequisites

The Whitepaper uses advanced Quarto features that require several external tools:

1. **Quarto** – The document rendering engine.
2. **LaTeX** – For PDF generation, using the `xelatex` engine.
3. **Python** – For inline Python code that generates diagrams and converts SVG logos. The Python environment must have the `graphviz`, `IPython`, and `cairosvg` packages installed (e.g., via `pip install graphviz IPython cairosvg`).
4. **Graphviz** – For rendering `dot` diagrams embedded in the document. This includes both the system Graphviz binaries (`dot` command) and the Python `graphviz` package.

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

# Install required Python packages for diagrams and SVG conversion
pip install graphviz IPython cairosvg
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

# Install required Python packages for diagrams and SVG conversion
pip install graphviz IPython cairosvg
```

### Windows

Download and install:

- Quarto from [quarto.org](https://quarto.org/docs/download/)
- MiKTeX or TeX Live for LaTeX
- Python from [python.org](https://www.python.org/downloads/) (ensure `pip` is installed)
- Graphviz from [graphviz.org](https://graphviz.org/download/) (both the binaries and the Python package)

Add the installation directories to your system PATH.

After installing Python, install the required Python packages for diagrams and SVG conversion via:

```bash
pip install graphviz IPython cairosvg
```

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

## Advanced Rendering Techniques

The Whitepaper uses several advanced Quarto features:

- **Three output formats**: HTML (for web viewing), GFM (GitHub‑Flavored Markdown), and PDF (for print). The format settings are defined in the YAML header of `Whitepaper.qmd`.
- **HTML output**: Custom CSS styling, embedded SVG figures, and self‑contained resources.
- **PDF output**: Uses `xelatex` engine. SVG logos are converted to PDF via Python’s `cairosvg` package. The LaTeX header includes custom packages (`authblk`, `unicode‑math`, `graphicx`, etc.) and layout adjustments.
- **Graphviz diagrams**: The document includes `dot` code blocks that are rendered to SVG (for HTML/Markdown) or PDF (for PDF) using the `_graphviz.py` helper module.
- **Conditional content**: Some blocks are visible only in specific formats (e.g., `{.content‑visible when‑format=\"gfm\"}`).

Refer to the source `Whitepaper.qmd` for the exact configuration.

## Document Structure

- `Whitepaper.qmd` – The source file containing the complete paper in Quarto Markdown.
- `_include/_graphviz.py` – Python module that provides `dot()` and `dot_svg()` functions for generating Graphviz diagrams.
- `_extensions/` – Contains Quarto extensions (currently only a custom extension for inline SVG).
- `Whitepaper_files/` – Directory created during rendering that holds generated SVG images and other auxiliary files.
- `Whitepaper.pdf` – The final PDF (already included in the repository).
- `Whitepaper.md` – The final Markdown version (already included in the repository).

## Troubleshooting

### LaTeX errors about missing packages

The document uses several LaTeX packages (`authblk`, `unicode‑math`, `graphicx`, `adjustbox`). If you encounter missing‑package errors, ensure you have a **full** LaTeX installation (e.g., `texlive‑full` on Linux, or the complete MacTeX bundle). You can also manually install missing packages with `tlmgr`.


### SVG images not appearing in PDF

If the CERN and other logos are missing in the PDF, verify that:

1. The Python `cairosvg` package is installed (via `pip install cairosvg`). This is required for SVG‑to‑PDF conversion.
2. The `Whitepaper_files` directory is writable and contains the generated `image0.svg` and `image1.svg` files after rendering.

### Graphviz diagrams not rendered

Ensure that:

1. The `dot` command (part of Graphviz) is in your `PATH`. Quarto will call `dot` to produce SVG diagrams; if `dot` is missing, the diagrams will be omitted.
2. The Python `graphviz` package is installed (via `pip install graphviz`). The `_graphviz.py` module depends on it.
3. The `IPython` package is installed if you are using Jupyter kernels.
4. If diagrams contain non‑ASCII characters, ensure your system’s locale supports UTF‑8. The `_graphviz.py` module normalizes Unicode to NFC form, but encoding issues may still arise.

### Python code block errors

The Python block is marked `eval: false`, so it is not executed during rendering. It only writes static SVG code into the `Whitepaper_files` folder. However, the block imports the `_graphviz.py` module, which requires the `graphviz` and `IPython` packages, and the SVG‑to‑PDF conversion uses the `cairosvg` package. If you encounter Python‑related errors, verify that:

1. Python is installed and the `os` and `tempfile` modules are available (they are part of the standard library).
2. The required Python packages are installed (`pip install graphviz IPython cairosvg`).
3. The `_include/_graphviz.py` file is present and readable.

## Updating the Whitepaper

To modify the Whitepaper, edit `Whitepaper.qmd` and then re‑run the `quarto render` commands above. Always commit both the source `.qmd` and the rendered `.pdf`/`.md` files to the repository.

## License

The Whitepaper text is licensed under CC BY‑NC‑ND 4.0. The build instructions in this README are provided under the same license as the rest of the SSCCS project (Apache‑2.0 for code, CC BY‑NC‑ND 4.0 for documentation).

## References

- [Quarto documentation](https://quarto.org/docs/)
- [LaTeX Project](https://www.latex-project.org/)
- [Graphviz](https://graphviz.org/)