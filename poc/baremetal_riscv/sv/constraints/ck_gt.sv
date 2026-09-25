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
// SSCCS Constraint: ck_gt — greater-than check
//
// RISC-V asm equivalent (observe_full.S:ck_gt):
//   ld  t0, 0(a0)
//   slt a0, a1, t0     // 1 if target < coord
//
// Synthesis: 1 comparator, 0 registers

module ck_gt #(
    parameter [63:0] THRESHOLD = 64'd0
) (
    input  logic [63:0] coord,
    output logic        result
);

    assign result = (coord > THRESHOLD);

endmodule
