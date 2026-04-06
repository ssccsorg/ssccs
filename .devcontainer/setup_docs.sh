#!/bin/bash
set -e

QUARTO_VER="1.9.35"
C2PA_VER="0.9.12"
REQUIREMENTS_TXT="docs/requirements.txt"
TEX_PACKAGES_TXT="docs/tex-packages.txt"

echo "=== SSCCS Docs DevContainer Setup ==="

echo "[1/5] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y graphviz librsvg2-bin
sudo apt-get clean

echo "[2/5] Installing Python dependencies..."
python3 -m pip install --upgrade pip
pip3 install -r "$REQUIREMENTS_TXT"

echo "[3/5] Installing Quarto ${QUARTO_VER}..."
if [ ! -f "/opt/quarto/bin/quarto" ]; then
    wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VER}/quarto-${QUARTO_VER}-linux-amd64.tar.gz"
    sudo mkdir -p /opt/quarto
    sudo tar -xzf "quarto-${QUARTO_VER}-linux-amd64.tar.gz" -C /opt/quarto --strip-components=1
    rm "quarto-${QUARTO_VER}-linux-amd64.tar.gz"
fi

echo "[4/5] Installing TinyTeX (CI method)..."
if [ ! -d "$HOME/.TinyTeX" ]; then
    curl -sL "https://yihui.org/tinytex/install-bin-unix.sh" | sh
else
    echo "TinyTeX already installed"
fi

# Use the fixed path that matches CI (now that platform is forced to amd64)
TLMGR="$HOME/.TinyTeX/bin/x86_64-linux/tlmgr"
if [ ! -f "$TLMGR" ]; then
    # Fallback: dynamic search just in case
    TLMGR=$(find "$HOME/.TinyTeX/bin" -name tlmgr -type f | head -1)
fi

if [ -z "$TLMGR" ] || [ ! -f "$TLMGR" ]; then
    echo "ERROR: tlmgr not found. TinyTeX installation failed."
    exit 1
fi

echo "Updating tlmgr..."
$TLMGR update --self

if [ -f "$TEX_PACKAGES_TXT" ]; then
    echo "Installing LaTeX packages from $TEX_PACKAGES_TXT..."
    PACKAGES=$(grep -v '^#' "$TEX_PACKAGES_TXT" | tr '\n' ' ')
    if [ -n "$PACKAGES" ]; then
        $TLMGR install $PACKAGES
    fi
else
    echo "WARNING: $TEX_PACKAGES_TXT not found – skipping LaTeX packages"
fi

echo "[5/5] Installing c2patool ${C2PA_VER}..."
if [ ! -f "$HOME/.local/bin/c2patool" ]; then
    mkdir -p "$HOME/.local/bin"
    curl -L "https://github.com/contentauth/c2patool/releases/download/v${C2PA_VER}/c2patool-v${C2PA_VER}-x86_64-unknown-linux-gnu.tar.gz" -o /tmp/c2patool.tar.gz
    tar -xzf /tmp/c2patool.tar.gz -C /tmp
    mv /tmp/c2patool/c2patool "$HOME/.local/bin/"
    chmod +x "$HOME/.local/bin/c2patool"
    rm -rf /tmp/c2patool /tmp/c2patool.tar.gz
fi

echo ""
echo "=== Setup Complete ==="
echo "Quarto: $(/opt/quarto/bin/quarto --version)"
echo "Python: $(python3 --version)"
# Display tlmgr version if found
if [ -n "$TLMGR" ]; then
    echo "TinyTeX: $($TLMGR --version | head -1)"
else
    echo "TinyTeX: installed but tlmgr not found"
fi
echo "c2patool: $($HOME/.local/bin/c2patool --version 2>/dev/null || echo $C2PA_VER)"
echo ""
echo "Build command: cd docs && python build.py"