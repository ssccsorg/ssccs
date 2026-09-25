// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (C) 2026 Taeho Lee
//
// This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
// You may redistribute and modify this documentation and make products using
// it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
// documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
// INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
// PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
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

module ck_range #(
    parameter [63:0] MIN_VAL = 64'd0,
    parameter [63:0] MAX_VAL = 64'd10
) (
    input  logic [63:0] coord,
    output logic        result
);

    assign result = (coord >= MIN_VAL) && (coord <= MAX_VAL);

endmodule
