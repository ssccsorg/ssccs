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
// SSCCS Constraint: ck_range_010 — hardcoded [0,10]
//
// RISC-V asm equivalent (observe_full.S:ck_range_0_10):
//   li  t1, 11
//   sltu a0, t0, t1   // coord < 11 → 1, else 0
//
// Synthesis: 1 LUT6 carry-chain comparator, 0 registers

module ck_range_010 (
    input  logic [63:0] coord,
    output logic        result
);

    // Unsigned comparison: coord < 11 covers [0,10]
    assign result = (coord < 64'd11);

endmodule
