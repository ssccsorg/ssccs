# The POC's anchors on an iCESugar-Pro

The SystemVerilog substrate on a device. The Rust workspace, the assembly under Spike and the SystemVerilog under
Verilator each pin the same scenario; this builds that SystemVerilog for an ECP5 and reads the verdict off a pin.

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

Which two constraints, and how they compose, is data. A fourth file holds one inquiry line: two selectors and a
composition bit for the narrow observation, and the same for the broad one. The image carries the units and reads
the selectors, so a different scheme changes the table and not the design.

The selector numbers are the core's, in `sv/_units.svh`, and the generator reads them from there rather than
repeating them. This image carries `UNIT_EVEN` and `UNIT_RANGE_010`; any other selector answers zero, so an
inquiry that names a unit the image does not carry fails rather than passes.

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
./build.sh rom                 # the anchors, the exchange control, and a different inquiry
./build.sh sim                 # Verilator: the table passes, the exchanged one does not, the other inquiry does
./build.sh build pass          # yosys, nextpnr-ecp5, ecppack
./build.sh flash pass          # write it, then release the reset
./build.sh read                # gpio read PA13
```

`build`, `flash` and `read` need tools Homebrew does not package: `nextpnr-ecp5` and `ecppack` from OSS CAD Suite
(set `OSS_CAD_SUITE` to its root), and `icesprog` (set `ICESPROG` to the binary).

The negative control is a second image. `anchor_rom.py --swap 1,3` exchanges the broad expectations of the two
lines that carry 3 and 10, which leaves the same coordinates and the same multiset of expectations, so a checksum
over the table would not notice. The die refuses it.

The second control is about this design rather than this table. `anchor_rom.py --generative` keeps the two units
and composes them the other way round, intersecting where the anchored broad observation unites, and computes the
expectations in the generator instead of reading them from the anchors. The same build answers the new inquiry,
which is what makes the units the image's and the scenario the table's.

## The image

| | pass | swap |
|---|---:|---:|
| `TRELLIS_COMB` | 270 / 24,288 | 164 / 24,288 |
| `DP16KD` | 0 | 0 |
| Clock | 120.77 MHz at 25 MHz | 141.86 MHz at 25 MHz |
| `pin_match` | 1 | 0 |
| Stage three | green | red |

The ROM is 720 bits in five lines plus a 14 bit inquiry line, so the flow maps it into logic rather
than block RAM. The clock is the board's
own crystal: five lines need no PLL, and a derived clock is a number the flow has to constrain separately.

## What it does not cover

`proj_div` is not in the image. It synthesizes to 8,626 LUT4, a third of the 25F, and no anchor here needs it.

`ssccs_xif_coprocessor.sv` is not in the image either, because no anchor here is issued as an instruction. It elaborates and synthesizes (281 LUT4), and its gate is `make -C sv xif-check`; putting it on the die needs a core to issue the instructions, and this image has none.

No claim about rate. The die compares one line per clock and reports a verdict; the timing above is what the place
and route flow reports, not a benchmark.
