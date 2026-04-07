#!/Bin/bash
set -e

REQUIREMENTS_TXT="docs/requirements.txt"
TEX_PACKAGES_TXT="docs/tex-packages.txt"
TLMGR="/root/.TinyTeX/bin/x86_64-linux/tlmgr"

if [ -f "$REQUIREMENTS_TXT" ]; then
    echo "Installing Python dependencies with sudo uv..."
    sudo -E uv pip install --system --break-system-packages -r "$REQUIREMENTS_TXT"
fi

# Install LaTeX package
if [ -f "$TEX_PACKAGES_TXT" ] && [ -f "$TLMGR" ]; then
    PACKAGES=$(grep -v '^#' "$TEX_PACKAGES_TXT" | tr '\n' ' ')
    [ -n "$PACKAGES" ] && $TLMGR install $PACKAGES
fi

echo "Done. Environment is ready."
python docs/build.py -h
echo "Run 'python docs/build.py --website' to build the whole documentation and generate the docs website."