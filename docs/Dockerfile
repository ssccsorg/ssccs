FROM --platform=linux/amd64 mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Integrated management of environment variables
ENV QUARTO_VER="1.9.35" \
    C2PA_VER="0.9.12" \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_TOOL_DIR=/opt/uv-tools \
    # Avoid Pandoc emulation crashes (required when using Apple Silicon)
    GHCRTS="-V0" \
    LUAOTFLOD_CACHE_DIR="/tmp/luaotfload-cache" \
    TEXMFVAR="/tmp/texmf-var" \
    PATH="/opt/quarto/bin:/opt/tinytex/bin/x86_64-linux:/usr/local/bin:${PATH}"

# Copy UV binary
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Install system packages and external tools (minimize layers)
RUN sed -i 's/archive.ubuntu.com/azure.archive.ubuntu.com/g' /etc/apt/sources.list.d/ubuntu.sources && \
    sed -i 's/security.ubuntu.com/azure.archive.ubuntu.com/g' /etc/apt/sources.list.d/ubuntu.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    python3 python-is-python3 graphviz librsvg2-bin wget curl ca-certificates sudo \
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* \
    # Install Quarto
    && wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VER}/quarto-${QUARTO_VER}-linux-amd64.tar.gz" \
    && mkdir -p /opt/quarto \
    && tar -xzf "quarto-${QUARTO_VER}-linux-amd64.tar.gz" -C /opt/quarto --strip-components=1 \
    && rm "quarto-${QUARTO_VER}-linux-amd64.tar.gz" \
    # Install c2patool
    && curl -L "https://github.com/contentauth/c2patool/releases/download/v${C2PA_VER}/c2patool-v${C2PA_VER}-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/c2patool.tar.gz \
    && tar -xzf /tmp/c2patool.tar.gz -C /tmp \
    && mv /tmp/c2patool/c2patool /usr/local/bin/ \
    && chmod +x /usr/local/bin/c2patool \
    && rm -rf /tmp/c2patool*

# Install binary
RUN uv tool install rumdl==0.1.86

# Install TinyTeX and LaTeX packages
RUN /opt/quarto/bin/quarto install tinytex --no-prompt \
    && mv /root/.TinyTeX /opt/tinytex \
    && /opt/tinytex/bin/x86_64-linux/tlmgr path add \
    && chmod -R 755 /opt/tinytex \
    && tlmgr install \
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
        translator \
    && luaotfload-tool --list=config

# Install Python dependencies (put the most frequently changing layers at the bottom)
RUN uv pip install --system --break-system-packages \
        PyYAML>=6.0 \
        graphviz>=0.20 \
        ipython>=8.0 \
        plotly>=5.0 \
        jupyter \
        matplotlib>=3.0 \
        numpy>=1.21 \
        cairosvg \
        jupyter-cache \
        scipy \
        networkx \
        requests
