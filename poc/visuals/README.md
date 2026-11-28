# The visual assets

The proof of concept ships three kinds of asset that a professional network or an agent can consume without a GUI: a timing diagram of the XIF handshake, a state diagram of its FSM, and coarse schematics of representative units. Each image is rendered from a text source by a command-line tool, so a change to the hardware regenerates the image instead of leaving a stale picture beside new code.

## What is here

| Source | Read from | Rendered |
|---|---|---|
| `wavedrom/xif_handshake.json5` | the FSM in `sv/ssccs_xif_coprocessor.sv` | `out/wavedrom/xif_handshake.svg`, `.png` |
| `graphviz/xif_fsm.dot` | the same next-state block | `out/graphviz/xif_fsm.svg`, `.png` |
| `graphviz/architecture.dot` | `README.md` and `_golden_anchors.svh` | `out/graphviz/architecture.svg`, `.png` |
| `netlistsvg/units.txt` | the SystemVerilog units | one schematic per unit, `out/netlist/<module>.svg`, `.png` |
| `layout/run.sh` | the coprocessor RTL and one ORFS design config | `docs/poc/figures/xif-die.svg`, `.png` and `xif-close.svg`, `.png` |

The schematic inputs are the units themselves. `gen.sh` reads each module named in `units.txt`, elaborates it with Yosys at a coarse level so comparators and adders stay as blocks, and lets NetlistSVG draw them. The timing and FSM diagrams are transcriptions of the module, so the module stays the source and the DOT or JSON5 file states the reading it makes.

## Requirements

- `yosys`, `dot` (Graphviz), and `node` with `npx`
- one of `rsvg-convert`, ImageMagick `magick` or `convert`, or `inkscape`

`netlistsvg` and `wavedrom-cli` are taken from `PATH` when installed and through `npx --yes` otherwise, pinned to `netlistsvg@1.0.2` and `wavedrom-cli@3.2.0`. The first `npx` run fetches the package. The POC CI renders these assets and publishes `visuals/` beside the POC README.

## Run

```bash
cd poc/visuals
./gen.sh
```

Images land in `out/`. Each family renders independently, and a missing renderer fails loudly instead of writing a partial set.

## Reading the timing diagram

The two issues show the two paths through `XIF_ACCEPT`. The first waits for `result_ready`, so the state holds in `XIF_ACCEPT` for two cycles and the result stays on the bus. The second completes in one cycle. `XIF_RESPOND` is a one-cycle bubble in both, during which neither `issue_ready` nor `result_valid` is asserted. The annotation marks the latency the formal property states: `result_valid` follows the issue handshake by one cycle.

## Extension

A new schematic is a new line in `netlistsvg/units.txt` with the module name and its path under `sv/`. A new hand-authored diagram is a new `.dot` or `.json5` file in its directory. No script names an individual file beyond the glob patterns.

## The layout

`layout/run.sh` carries the XIF coprocessor through SkyWater 130 nm synthesis, place and route with ORFS, and writes the two figures the PoC page shows: the die from above and a close view of its centre. It runs the ORFS Docker image, which is x86_64 and runs on x86 natively or on Apple Silicon under Rosetta.

The design configuration and the timing constraint live in `layout/designs/sky130hd/ssccs_xif/`, and the RTL is mounted read-only from `baremetal_riscv/sv`, so the flow reads the units the simulators read. The clock is the carrier's 25 MHz crystal.

The renderer belongs to the syntagma hardware tree; point `RENDER_GDS` at it to draw the figures as well:

```bash
cd poc/visuals/layout
RENDER_GDS=../../../syntagma/hw/visuals/render_gds.py ./run.sh
```

The figures land in `docs/poc/figures/`. The flow's own tree, `layout/out/` and `layout/results/`, holds only build products and is not tracked.

## Limits

The timing and FSM diagrams are readings of the module, not output of a simulator. The schematics show structure, not timing or area. The layout is one revision placed at one clock constraint; a different library or constraint moves its numbers. None of these images is a verification claim. The claims live in the golden anchors and the testbenches.
