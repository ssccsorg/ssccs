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

The die reads the line's coordinate, runs `ck_even`, `ck_range_010` and `observe` over it, and compares both
results with the line's own. A pass closes when no line disagrees, so a single wrong coordinate is the same size
as the whole table. The four modules are the POC's, unchanged.

`anchor_rom.py` writes the three tables from `sv/_golden_anchors.svh`. A table transcribed by hand is a table the
anchors do not have to hold, so the ROM is generated and the generator refuses if the three tables disagree in
length or if the reject sentinel in the file is not the one `observe` emits.

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
./build.sh rom                 # the anchors, and the same table with two expectations exchanged
./build.sh sim                 # Verilator: the table passes, the exchanged one does not
./build.sh build pass          # yosys, nextpnr-ecp5, ecppack
./build.sh flash pass          # write it, then release the reset
./build.sh read                # gpio read PA13
```

`build`, `flash` and `read` need tools Homebrew does not package: `nextpnr-ecp5` and `ecppack` from OSS CAD Suite
(set `OSS_CAD_SUITE` to its root), and `icesprog` (set `ICESPROG` to the binary).

The negative control is a second image. `anchor_rom.py --swap 1,3` exchanges the broad expectations of the two
lines that carry 3 and 10, which leaves the same coordinates and the same multiset of expectations, so a checksum
over the table would not notice. The die refuses it.

## The image

| | pass | swap |
|---|---:|---:|
| `TRELLIS_COMB` | 153 / 24,288 | 162 / 24,288 |
| `DP16KD` | 0 | 0 |
| Clock | 133.69 MHz at 25 MHz | 126.44 MHz at 25 MHz |
| `pin_match` | 1 | 0 |
| Stage three | green | red |

The ROM is 720 bits in five lines, so the flow maps it into logic rather than block RAM. The clock is the board's
own crystal: five lines need no PLL, and a derived clock is a number the flow has to constrain separately.

## What it does not cover

`proj_div` is not in the image. It synthesizes to 8,626 LUT4, a third of the 25F, and no anchor here needs it.

`ssccs_xif_coprocessor.sv` is not in the image either, because no anchor here is issued as an instruction. It elaborates and synthesizes (281 LUT4), and its gate is `make -C sv xif-check`; putting it on the die needs a core to issue the instructions, and this image has none.

No claim about rate. The die compares one line per clock and reports a verdict; the timing above is what the place
and route flow reports, not a benchmark.
