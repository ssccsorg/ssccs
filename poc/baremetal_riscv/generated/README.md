# Generated modules

The landing place for SystemVerilog the host emitter writes. Nothing here is committed except this file and the
ignore rule: an emitted module is a build artifact, and the emitter is its source.

## The contract

| | |
|---|---|
| Written by | the host emitter, from a Scheme's constraints, projector and composition |
| Compiled by | `make -C sv elaborate`, over whatever is present |
| Built for a board | the board's flow, given the generated module as its top |
| Committed | never |

A generated module must not share a name with a unit under `sv/`, because the elaboration gate reads both in one
pass and a duplicate definition would be ambiguous.

The gate exists before the emitter does. That order matters: an emitter with no consumer can emit anything and
still look finished, and the first consumer it gets is the one that says whether the output is a design.
