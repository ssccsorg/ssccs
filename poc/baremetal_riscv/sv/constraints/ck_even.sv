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
// SSCCS Constraint: ck_even
// SystemVerilog Reference — purely combinational, zero branches
//
// RISC-V asm equivalent (observe_full.S:ck_even):
//   ld   t0, 0(a0)    // load i64
//   andi t0, t0, 1    // mask LSB
//   xori a0, t0, 1    // 1=even, 0=odd
//
// Synthesis: 1 LUT6 (3-input XOR of AND result), 0 registers

module ck_even (
    input  logic [63:0] coord,
    output logic        result
);

    // coord[0] == 0  →  even  →  result = 1
    // coord[0] == 1  →  odd   →  result = 0
    assign result = ~coord[0];

endmodule
