#!/bin/bash
set -e

echo "Setup TinyTeX permissions..."
sudo chown -R "$(whoami)" /opt/tinytex
quarto check

if [ -f "build.py" ]; then
    python docs/build.py -h
fi

echo -e "\nOwnership secured. Environment is ready."
echo -e "\nRun: python docs/build.py"