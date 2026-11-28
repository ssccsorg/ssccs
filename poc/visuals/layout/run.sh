#!/usr/bin/env bash
# SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
# Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
#
# Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
# concept: a copy carries this notice and the revision it was taken from.
#
# Carry the XIF coprocessor to a SkyWater 130 nm layout: ORFS in its Docker
# image for synthesis, place and route, then the metal stack drawn from the
# flow's final GDS.
#
# The flow runs in a Docker volume and its reports are read into a scratch
# directory, so the repository holds the figures and no build product.
#
# The image is x86_64. The flow runs on x86 natively and on Apple Silicon under
# Rosetta.
#
# Usage:
#   ./run.sh
#
# The renderer belongs to the syntagma hardware tree. Point RENDER_GDS at it to
# draw the figures as well:
#   RENDER_GDS=../../../syntagma/hw/visuals/render_gds.py ./run.sh

set -euo pipefail

VIS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_DIR="$(cd "$VIS_DIR/../.." && pwd)"
SV_DIR="$POC_DIR/baremetal_riscv/sv"
# The figures are documentation assets, so they land beside the page that shows them.
FIGS="${FIGS:-$(cd "$VIS_DIR/../../../docs/poc/figures" && pwd)}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

IMG=${ORFS_IMAGE:-openroad/orfs:latest}
VOL=${ORFS_VOLUME:-ssccs_poc_orfs}
FLOW=/OpenROAD-flow-scripts/flow
CONFIG=designs/sky130hd/ssccs_xif/config.mk

need() {
    command -v "$1" >/dev/null 2>&1 || {
        echo "missing required tool: $1" >&2
        exit 1
    }
}

need docker

echo "--- ORFS: sky130hd flow for ssccs_xif_coprocessor ---"
docker run --rm --platform linux/amd64 \
    -v "${VOL}:${FLOW}" \
    -v "${VIS_DIR}/designs:${FLOW}/designs" \
    -v "${SV_DIR}:${FLOW}/designs/src/ssccs_xif:ro" \
    "${IMG}" bash -c "cd ${FLOW} && make DESIGN_CONFIG=${CONFIG}" \
    2>&1 | tee "${WORK}/orfs.log" | tail -30

echo "--- read the flow's results ---"
docker run --rm --platform linux/amd64 \
    -v "${VOL}:${FLOW}" \
    -v "${WORK}:/out" \
    "${IMG}" bash -c "cp -r ${FLOW}/results/sky130hd/ssccs_xif /out/ 2>/dev/null || true"

GDS="${WORK}/ssccs_xif/base/6_final.gds"
test -f "${GDS}" || {
    echo "the flow wrote no 6_final.gds; its log follows" >&2
    tail -40 "${WORK}/orfs.log" >&2
    exit 1
}
echo "gds: ${GDS}"

if [ -n "${RENDER_GDS:-}" ]; then
    mkdir -p "${FIGS}"
    echo "--- draw the metal stack ---"
    uv run --python 3.11 --with gdstk --with matplotlib python "${RENDER_GDS}" \
        --gds "${GDS}" --def "${WORK}/ssccs_xif/base/6_final.def" \
        --out "${FIGS}" --name xif-die --crop die --size 2400 \
        --layers 68,69,70,71,72 --palette mono --merge --frame --svg
    uv run --python 3.11 --with gdstk --with matplotlib python "${RENDER_GDS}" \
        --gds "${GDS}" --def "${WORK}/ssccs_xif/base/6_final.def" \
        --out "${FIGS}" --name xif-close --crop 78,78,158,158 --size 1800 \
        --layers 68,69,70,71,72 --palette mono --merge --frame --svg
fi

echo "figures in ${FIGS}"
