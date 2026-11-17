# The POC's anchors on an iCESugar-Pro

The SystemVerilog substrate on a device. The Rust workspace, the assembly under Spike and the SystemVerilog under
Verilator each pin the same scenario; this builds that SystemVerilog for an ECP5 and reads the verdict off a pin.

Two images live here and share the carrier's pins, the three anchor tables and the verdict logic. They differ in
where the constraint comes from. `ssccs_anchor_board` carries kinds and bounds as data and answers an inquiry its
fabric never saw. `ssccs_generated_board` carries a constraint the host emitter wrote into two modules, with the
bounds baked in. The anchors grade both, so over the same table the two must return the same verdict.

A third image is the two halves of a substrate together and no table of points at all. `ssccs_decoded_board` sweeps
an address space, an emitted decoder turns each address into the coordinate the Scheme holds there, and an emitted
observation module decides whether that coordinate is admissible. The die counts the admissions and compares the
total with the number the host computed from the same Scheme and the same program.

This folder belongs to the POC, not to a project built on it. The POC is the layer the projects materialize, so the
image is built from the POC's own modules and its own anchors file. The only thing it shares with any other board
work is the carrier's pin map, which is a property of the board.

## What it checks

The scenario's five anchors, one line at a time. Each line carries a coordinate and the two results the scenario
expects for it: the narrow observation (even and in range) and the broad one (even or in range).

| Line | Coordinate | Narrow | Broad |
|---:|---:|---|---:|
| 0 | 2 | 2 | 2 |
| 1 | 3 | reject | 3 |
| 2 | 5 | reject | 5 |
| 3 | 10 | 10 | 10 |
| 4 | 12 | reject | 12 |

The die reads the line's coordinate, computes the two observations over it, and compares both results with the
line's own. A pass closes when no line disagrees, so a single wrong coordinate is the same size as the whole table.

## Where the constraint lives

The data image carries a fourth file with a descriptor and eight operands: a kind and two 64-bit bounds for each
of the four slots the descriptor names, two slots per observation. The kinds are the core's, in `sv/_units.svh`,
and the generator reads them from there rather than repeating them.

| Kind | Unit | Bound |
|---:|---|---|
| 0 | `UNIT_EVEN` | none |
| 1 | `UNIT_RANGE` | minimum and maximum |
| 2 | `UNIT_EQ` | the value compared against |
| 3 | `UNIT_GT` | the threshold |

A kind the image does not carry answers zero, so an inquiry naming one fails rather than passes. Which kinds, which
bounds, and which composition is in that file, so a different constraint changes the table and not the design.

The generated image has no such file. `make -C sv generate` writes `ssccs_generated_narrow` and
`ssccs_generated_broad` from a constraint program, and this top reads the coordinate, the narrow result and the
broad result. The same constraint is a module rather than a row, so a different constraint there is a different
module: the emitter is the source, and this image is one build of it. What it cannot do follows from that. A
program fixed at generation time has no answer for a kind it was not generated for, so the generative inquiry has
no image here and stays on the data one.

`anchor_rom.py` writes the four files from `sv/_golden_anchors.svh`. Values transcribed by hand are values the
anchors do not have to hold, so the ROM is generated and the generator refuses if the three tables disagree in
length or if the reject sentinel in the file is not the one `observe` emits. The scenario itself is the fixture's,
and it is the only part of this folder written from the scenario: even and the constant range, intersected for the
narrow observation and united for the broad one.

## The pins

| Net | Ball | iCELink pin | Direction |
|---|---|---|---|
| `clk_in` | P6 | none | 25 MHz crystal |
| `stage[0]` | N4 | PA0 | host drives |
| `stage[1]` | J5 | PA1 | host drives |
| `pin_match` | H5 | PA13 | host reads |
| `led_green` | A11 | none | RGB, active high |
| `led_blue` | A12 | none | RGB, active high |
| `led_red` | B11 | none | RGB, active high |

`stage` selects a colour and blinks it, except stage three, which is the verdict and is steady: green when every
line agreed and red when one did not. PA14 on F5 is the iCELink's SWD clock, which is why the stage is two bits.

## Commands

```sh
./build.sh rom                        # the anchors, the exchange control, and a different inquiry
./build.sh sim [data|generated|decoded]         # Verilator: the tables, or the decoded space and its control
./build.sh build [pass|swap] [data|generated|decoded]   # yosys, nextpnr-ecp5, ecppack
./build.sh flash [pass|swap] [data|generated|decoded]   # write it, then release the reset
./build.sh read                       # gpio read PA13
```

The image word is `data` when it is left out. `sim generated` runs the pass and swap tables only, `sim decoded`
runs the host's count and one off it, and `build`, `flash` and `read` take the word the same way.

## The decoded image

The space is a line of sixteen points three apart, so the address is not the coordinate and the decode is a
multiplication rather than a wire. The program is `even and range [0, 10]`, which admits 0 and 6 out of the
sixteen.

The count separates the cases. A decoder that passed the address through would count six admissible points,
parity alone would count eight and the range alone four, so the die reporting two says the decode, the parity and
the bound all did their work.

Nothing in the image names the Scheme or the program. `make -C sv generate` writes the decoder, the observation
module and the two counts, and the flow reads the address count from the same place. A different Scheme or a
different program is a different module and a different number.

`build`, `flash` and `read` need tools Homebrew does not package: `nextpnr-ecp5` and `ecppack` from OSS CAD Suite
(set `OSS_CAD_SUITE` to its root), and `icesprog` (set `ICESPROG` to the binary).

The negative control is a second image. `anchor_rom.py --swap 1,3` exchanges the broad expectations of the two
lines that carry 3 and 10, which leaves the same coordinates and the same multiset of expectations, so a checksum
over the table would not notice. The die refuses it.

The second control is about this design rather than this table. `anchor_rom.py --generative` writes coordinates
and an inquiry the scenario never uses: -2 among the five points, a threshold of -1, and a range from -10 to 10
united with an equality. It computes the expectations in the generator instead of reading them from the anchors,
and the same build answers the new inquiry. What the image holds is the kinds, and what the table holds is the
constraint.

That table is also the signedness check. A coordinate is the space's own i64, so `ck_range` and `ck_gt` compare
signed, as the reference assembly does with `slt`. Flip either unit to an unsigned compare and the anchored tables
still pass, because their bounds are non-negative, while the third table fails: the die rejects the point it should
accept. On the carrier that image answers 1, which is the die saying its order is the space's.

## The images

| | data: pass | data: swap | data: other inquiry | generated: pass | generated: swap |
|---|---:|---:|---:|---:|---:|
| `TRELLIS_COMB` | 145 / 24,288 | 150 / 24,288 | 313 / 24,288 | 139 / 24,288 | 150 / 24,288 |
| `DP16KD` | 0 | 0 | 0 | 0 | 0 |
| Clock | 154.66 MHz | 143.82 MHz | 92.13 MHz | 137.49 MHz | 142.80 MHz |
| `pin_match` | 1 | 0 | 1 | 1 | 0 |
| Stage three | green | red | green | green | red |

The decoded image is measured on its own, because it has no table to vary:

| | decoded |
|---|---:|
| `TRELLIS_COMB` | 157 / 24,288 |
| `DP16KD` | 0 |
| Clock | 66.27 MHz |
| `pin_match` | 1 |
| Stage three | green |

Every column answers the same five anchors except the last, which counts its own space. The two `pass` columns are
the same table read by two designs, and the two `swap` columns are the negative control in both. The decoded image
costs more logic than either table reader and closes lower: a multiplier and a 64-bit accumulator replace a five
line ROM, and at this size the arithmetic is the expensive part.

The area follows the table rather than the design, because the flow maps the ROM into logic: five lines of three
64-bit words are cheaper as gates than as a block RAM, so a different set of constants is a different amount of
logic. The third column is the largest because a kind the inquiry never names is optimised away, and the build that
names the unused kinds carries the decode for all four.

The generated image is smaller than the data one on the same table, since it has no inquiry ROM and no
kind selects, and its constraint network is two units rather than eight instances behind four five-way muxes. At
this size both images are dominated by the same 25-bit counter, the comparison and the ROM, so the difference is
a handful of LUTs rather than a ratio. The clock numbers are the place and route flow's own, not a benchmark.

The data image's ROM is 720 bits in five lines plus a 14 bit inquiry line, and the generated image's is the same
three tables without the inquiry. The clock is the board's own crystal: five lines need no PLL, and a derived
clock is a number the flow has to constrain separately.
## What it does not cover

`proj_div` is not in the image. It synthesizes to 8,626 LUT4, a third of the 25F, and no anchor here needs it.

`ssccs_xif_coprocessor.sv` is not in the image either, because no anchor here is issued as an instruction. It elaborates and synthesizes (281 LUT4), and its gate is `make -C sv xif-check`; putting it on the die needs a core to issue the instructions, and this image has none.

No claim about rate. The die compares one line per clock and reports a verdict; the timing above is what the place
and route flow reports, not a benchmark.
