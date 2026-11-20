// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Research in progress. Read, check, and cite it. See LICENSE at the root of
// this proof of concept before copying it into another work.
//
// SSCCS Constraint: ck_range — parameterized [min, max]
//
// RISC-V asm equivalent (observe_full.S:ck_range):
//   slt  t1, t0, a1     // coord < min ?
//   slt  t2, a2, t0     // max < coord ?
//   or   t0, t1, t2     // out of range ?
//   xori a0, t0, 1      // invert: 1 = in range
//
// Synthesis: 2 comparators + OR + NOT, 0 registers

module ck_gt (
    input  logic [63:0] coord,
    input  logic [63:0] threshold,
    output logic        result
);

    // Signed, for the same reason ck_range is: the space's order is i64's.
    assign result = ($signed(coord) > $signed(threshold));

endmodule
