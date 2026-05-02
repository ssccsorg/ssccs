#!/bin/bash
set -e

quarto check

if [ -f "build.py" ]; then
    python docs/build.py -h
fi

echo -e "\nOwnership secured. Environment is ready."
echo -e "\nRun: python docs/build.py"
