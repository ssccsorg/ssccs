# Generated modules

The landing place for SystemVerilog the host emitter writes. Nothing here is committed except this file and the
ignore rule: an emitted module is a build artifact, and the emitter is its source.

## The contract

| | |
|---|---|
| Written by | `make -C sv generate`, which runs `ssccs-hardware-mapping`'s `emit-observation` binary |
| Compiled by | `make -C sv elaborate`, over whatever is present |
| Checked by | `make -C sv generated-check`, which answers the golden anchors in simulation |
| Built for a board | the board's flow, given the generated module as its top |
| Committed | never |

A generated module must not share a name with a unit under `sv/`, because the elaboration gate reads both in one
pass and a duplicate definition would be ambiguous.

The gate exists before the emitter does. That order matters: an emitter with no consumer can emit anything and
still look finished, and the first consumer it gets is the one that says whether the output is a design.

## What is written

Two modules, from one constraint set joined twice:

| Module | Admissible set |
|---|---|
| `ssccs_generated_narrow` | `even and range [0, 10]` |
| `ssccs_generated_broad` | `even or range [0, 10]` |

They are the pair `sv/_golden_anchors.svh` already carries, so the emitted modules are graded by the anchors rather
than by a table written for them: the narrow module must reproduce `GOLDEN_NARROW` and the broad one `GOLDEN_BROAD`
over `GOLDEN_SEG`. A program with other bounds is a program the binary is told about, not a program this file
names.

The stamp `.emitted` records that the modules match the emitter's current sources. Deleting it, or touching a file
under `crates/hardware-mapping/src` or `crates/core/src`, writes them again.

## The case that is not here

These modules bake their bounds as structure. The board's unit table carries a kind and its operands as data, so
one image answers an inquiry its fabric never saw. That image is hand-written under `boards/`, and the two cases
are different designs rather than two settings of one.
