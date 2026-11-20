// SPDX-License-Identifier: LicenseRef-Proprietary
// Copyright (C) 2026 Taeho Lee, SSCCS Initiative. All rights reserved.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
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

module ck_range (
    input  logic [63:0] coord,
    input  logic [63:0] min_val,
    input  logic [63:0] max_val,
    output logic        result
);

    // Signed, because a coordinate is an i64 and the reference assembly compares with slt. An unsigned compare
    // would put every negative coordinate above every positive one.
    assign result = ($signed(coord) >= $signed(min_val)) && ($signed(coord) <= $signed(max_val));

endmodule
