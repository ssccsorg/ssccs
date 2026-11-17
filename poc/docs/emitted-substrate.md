# The emitted substrate

The POC writes a constraint into two substrates and builds one of them onto a carrier. This entry states the
description both lowerings take, the path from a program to a bitstream, and the parts of the substrate the host
does not write.

## The description

`ssccs_core::ConstraintSpec` is a kind and its bound: `Even`, `Range { min, max }`, `Eq { value }`, `Gt { value }`.
It is data. `eval_constraint` is its host semantics, and every lowering is checked against that function, so a
substrate that disagrees is wrong by definition rather than by preference.

The kinds are the substrate's vocabulary and not the whole constraint language. A constraint outside this list has
no unit, which is why the list is short.

## The two lowerings

The assembly emitter, `ssccs_examples::constraint_emitter`, writes one branchless function per spec for the
reference simulation: a comparison and a mask, no conditional branch, constants baked in, and golden comments that
pin the generated function to `eval_constraint` over a fixture.

The SystemVerilog emitter, `ssccs_hardware_mapping::sv_emit`, writes a module for a whole composition: one instance
per constraint of the unit the kind names, the bound as a 64-bit two's complement literal, the declared join of the
results, a projector unit, and `observe`.

The second inherits the signed comparison from the units rather than restating it. `ck_range` and `ck_gt` compare
with `$signed`, which is the order the reference assembly uses, and an emitter that inlined the comparison would be
a second definition of the same constraint.

`ProjectorUnit` lists the projector units that take one coordinate and return one. A unit with two input ports is
absent on purpose: the emitted instance wires `coord` to `result`, so a two-input unit would leave a port
unconnected and the design would answer something the program never stated. A program needing one of those gets a
module written for it.

## The path

| Step | Command | What it says |
|---|---|---|
| emit | `make -C sv generate` | `ssccs-hardware-mapping`'s `emit-observation` writes two modules into `baremetal_riscv/generated/` |
| simulate | `make -C sv generated-check` | both modules answer `GOLDEN_SEG` with `GOLDEN_NARROW` and `GOLDEN_BROAD` |
| elaborate | `make -C sv elaborate` | every module, emitted ones included, reads under yosys |
| build | `./build.sh build pass generated` | the modules are a design with an area and a clock |

Nothing under `generated/` is committed. A stamp records that the modules match the emitter's sources, so a change
to the emitter or to the description writes them again.

The two emitted programs carry the same constraints and differ only in the join, so the pair names what the
composition operator does: `even and range [0, 10]` admits two of the five anchored coordinates, `even or range
[0, 10]` admits all five.

## The images

`boards/icesugar_pro` holds three. The first two drive the same seven nets, read the same three anchor tables, and
carry the same sweep, fill and verdict logic; they differ in where the constraint comes from. The third has no
table of points at all.

| | data: pass | data: swap | data: other inquiry | generated: pass | generated: swap |
|---|---:|---:|---:|---:|---:|
| `TRELLIS_COMB` | 145 | 150 | 313 | 139 | 150 |
| Clock | 154.66 MHz | 143.82 MHz | 92.13 MHz | 137.49 MHz | 142.80 MHz |
| `pin_match` | 1 | 0 | 1 | 1 | 0 |

The decoded image takes 157 LUT4 and closes at 66.27 MHz, and answers 1. It costs more than either table reader
because a multiplier and a 64-bit accumulator replace a five line ROM: at this size the arithmetic is the expensive
part, and that is worth knowing before the space grows.

Every column answers the same five anchors except the decoded one, which counts its own space. The two pass columns
are the same table read by two designs, and the two swap columns are the negative control in both.
two swap columns are the negative control in both: two expectations exchanged leaves the same coordinates and the
same multiset of results, so a checksum over the table would not notice.

The generated image is smaller on the same table because it has no inquiry ROM and no kind selects. At this size
both are dominated by the counter, the comparison and the ROM, so the difference is a few LUTs rather than a ratio,
and the clock figures are the flow's own rather than a benchmark.

The simulation gate has teeth because the anchors disagree with a module that does nothing. A narrow module that
tied its constraint to one would answer 3 and 5, which those lines expect to be rejected, and `generated-check`
would fail on the first of them.

## What the host does not write

The bounds are structure. The inquiry table keeps a kind and its operands as data, so one image answers a
constraint its fabric never saw, and that image is hand-written. The two cases are different designs rather than
two settings of one, and neither substitutes for the other.

The Scheme half is partly emitted. `ssccs_hardware_mapping::address_decode` derives each axis's offset, step and
size from a Scheme's own segments and writes a decoder: an address in, one coordinate per axis out, with `valid`
low past the last segment. A Scheme that is not a product of equally spaced axes is refused rather than encoded,
because a decoder over an arbitrary set would be a table. What stays hand-written is the sweep, the fill, the
mismatch count and the verdict, which are the harness rather than the Scheme.

The decoder's check is a sweep: `make -C sv decode-check` drives every address and compares the module's arithmetic
against a table the host wrote from the Scheme's segments. One side divides, the other looks up, so an address that
lands on different coordinates in the two is a disagreement between two derivations of one space.

The generative channel belongs to the data image. A program fixed at generation time cannot answer a kind it was
not generated for, so the inquiry of unused kinds, which is also the signedness check, has no image on the emitted
side.

## Evidence

- `cargo test -p ssccs-hardware-mapping`: the literal form of a negative bound, the join that is emitted, the empty
  program, and the fact that the reject sentinel is not written by the emitter but comes from `observe`
- `cargo test --workspace --all-targets --release`
- `make -C sv check`: generation, the anchor table in simulation, the composition and XIF testbenches, elaboration
- `./build.sh all`: both images at the pass and swap tables, and the generative inquiry on the data image
- `./run.sh --validation`: the whole set in one command, with 13 binaries and both board images

## Open

A decoded space is on a carrier now, and it is the two halves together. `boards/icesugar_pro/ssccs_decoded_board.sv`
sweeps a sixteen point line, decodes each address to its coordinate, applies the emitted observation module and
compares the admission count with the host's. It has no table of points, and the count separates a decoder that
works from one that passes the address through.

Scheme determinism came with the decoder. `Scheme` held its segments in a `HashMap`, whose iteration order changes
between runs, so "enumerate a Scheme" was not reproducible and an address map had nothing to be defined on. The
segments are a `BTreeMap` now, ordered by identity.

An emitted model that reads a bound at run time has no emitter. The unit table on the board is still the only
place a constraint is data rather than structure, and it is hand-written.
