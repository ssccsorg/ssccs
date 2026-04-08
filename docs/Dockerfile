FROM --platform=linux/amd64 mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ENV QUARTO_VER="1.9.35" \
    C2PA_VER="0.9.12" \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    UV_SYSTEM_PYTHON=1 \
    # Avoid Pandoc emulation crashes (required when using Apple Silicon)
    GHCRTS="-V0" \
    LUAOTFLOD_CACHE_DIR="/tmp/luaotfload-cache" \
    TEXMFVAR="/tmp/texmf-var" \
    PATH="/opt/quarto/bin:/opt/tinytex/bin/x86_64-linux:/usr/local/bin:${PATH}"

# Fast Python package installer
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# system package
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python-is-python3 graphviz librsvg2-bin wget curl ca-certificates sudo \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install Quarto
RUN wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VER}/quarto-${QUARTO_VER}-linux-amd64.tar.gz" \
    && mkdir -p /opt/quarto \
    && tar -xzf "quarto-${QUARTO_VER}-linux-amd64.tar.gz" -C /opt/quarto --strip-components=1 \
    && rm "quarto-${QUARTO_VER}-linux-amd64.tar.gz"

# c2patool (need to check gnu version to prevent musl-based errors, keep as is)
RUN curl -L "https://github.com/contentauth/c2patool/releases/download/v${C2PA_VER}/c2patool-v${C2PA_VER}-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/c2patool.tar.gz \
    && tar -xzf /tmp/c2patool.tar.gz -C /tmp \
    && mv /tmp/c2patool/c2patool /usr/local/bin/ \
    && chmod +x /usr/local/bin/c2patool \
    && rm -rf /tmp/c2patool*

# TinyTeX installation and path optimization
RUN /opt/quarto/bin/quarto install tinytex --no-prompt \
    && mv /root/.TinyTeX /opt/tinytex \
    # Create a system symbolic link (this is required for the lualatex command to work anywhere)
    && /opt/tinytex/bin/x86_64-linux/tlmgr path add \
    && chmod -R 755 /opt/tinytex

# Create font cache directory
RUN mkdir -p /tmp/luaotfload-cache /tmp/texmf-var && chmod -R 777 /tmp/luaotfload-cache /tmp/texmf-var

# Install LaTeX package
RUN tlmgr update --self --all && \
    tlmgr install \
        babel-english \
        everypage \
        background \
        tcolorbox \
        tikzfill \
        pdfcol \
        caption \
        koma-script \
        libertinus-fonts \
        libertinus-type1 \
        libertinust1math \
        newtx \
        microtype \
        beamer \
        translator

# Python dependencies
RUN uv pip install --system --break-system-packages \
        PyYAML>=6.0 \
        graphviz>=0.20 \
        ipython>=8.0 \
        plotly>=5.0 \
        jupyter \
        matplotlib>=3.0 \
        numpy>=1.21 \
        cairosvg