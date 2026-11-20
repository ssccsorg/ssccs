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

module ck_range_010 (
    input  logic [63:0] coord,
    output logic        result
);

    // The bound belongs to the scheme this scenario states, so it is wired here as constants rather than kept as a
    // second implementation of the comparison.
    ck_range u_range (
        .coord(coord),
        .min_val(64'd0),
        .max_val(64'd10),
        .result(result)
    );

endmodule
