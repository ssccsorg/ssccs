FROM --platform=linux/amd64 mcr.microsoft.com/devcontainers/base:ubuntu-24.04

ENV QUARTO_VER="1.9.35" \
    C2PA_VER="0.9.12" \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    UV_SYSTEM_PYTHON=1 \
    # PATH setting: /usr/local/bin is included by default, so no additional confirmation is required.
    PATH="/opt/quarto/bin:/root/.local/bin:/root/.TinyTeX/bin/x86_64-linux:${PATH}"

# 2. Import the uv binary (do this first to utilize cache)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Layer integration installation (optimize build speed and capacity)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python-is-python3 graphviz librsvg2-bin wget curl ca-certificates \
    # ---A. Installing Quarto ---
    && wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VER}/quarto-${QUARTO_VER}-linux-amd64.tar.gz" \
    && mkdir -p /opt/quarto \
    && tar -xzf "quarto-${QUARTO_VER}-linux-amd64.tar.gz" -C /opt/quarto --strip-components=1 \
    && rm "quarto-${QUARTO_VER}-linux-amd64.tar.gz" \
    # ---B. Install c2patool (utilize environment variables and fix path) ---
    && curl -L "https://github.com/contentauth/c2patool/releases/download/v${C2PA_VER}/c2patool-v${C2PA_VER}-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/c2patool.tar.gz \
    && tar -xzf /tmp/c2patool.tar.gz -C /tmp \
    && mv /tmp/c2patool/c2patool /usr/local/bin/ \
    && chmod +x /usr/local/bin/c2patool \
    # ---C. Install TinyTeX ---
    && curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh \
    # ---D. Cleanup and Verification ---
    && apt-get clean -y && rm -rf /var/lib/apt/lists/* /tmp/c2patool* \
    && quarto --version && c2patool --version