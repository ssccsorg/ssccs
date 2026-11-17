# Generated modules

The landing place for SystemVerilog the host emitter writes. Nothing here is committed except this file and the
ignore rule: an emitted module is a build artifact, and the emitter is its source.

## The contract

| | |
|---|---|
| Written by | `make -C sv generate`, which runs `ssccs-hardware-mapping`'s `emit-observation` and `emit-decode` binaries |
| Compiled by | `make -C sv elaborate`, over whatever is present |
| Checked by | `make -C sv generated-check`, which answers the golden anchors in simulation, and `decode-check`, which sweeps a decoded space |
| Built for a board | `boards/icesugar_pro`, as `ssccs_generated_board`'s constraint |
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

## The address decoder

`ssccs_address_decode` is the other kind of module: its input is an address and its output is the coordinate a
Scheme holds there, one port per axis, with `valid` low past the last segment. The emitter derives the extents from
the Scheme's segments, so a different Scheme is a different module.

`decode-check` sweeps every address against `address_coord0.hex` and `address_coord1.hex`. The module divides and
the tables are a lookup, and both come from the same Scheme by different routes, so the sweep is a comparison rather
than a repetition. The demo space is a four by three grid; the emitter's own tests cover one axis and three.

## Where they are consumed

Two places, and they check different things. `sv/tb/generated_observation_tb.sv` drives them with the golden
coordinates and compares both observations against `GOLDEN_NARROW` and `GOLDEN_BROAD`, which says what they
compute. `boards/icesugar_pro/ssccs_generated_board.sv` builds them onto the ECP5 beside the data-driven image on
the same carrier, which says they are a design: 139 LUT4 and 137.49 MHz at the pass table, against 145 and
154.66 MHz for the image whose constraint is a table. Both images answer the same five anchors.

## The case that is not here

These modules bake their bounds as structure. The board's unit table carries a kind and its operands as data, so
one image answers an inquiry its fabric never saw. That image is hand-written under `boards/`, and the two cases
are different designs rather than two settings of one.
