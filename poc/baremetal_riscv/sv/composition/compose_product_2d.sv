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
// SSCCS Composition: Product (×) for 2×1D
// C((x,y)) = C₁(x) ∧ C₂(y)
//
// RISC-V asm equivalent (observe_full.S:compose_product_2d):
//   left  = coord[0]; call fa(left)  → C₁
//   right = coord[1]; call fb(right) → C₂
//   and a0, t0, t0    // C₁ ∧ C₂
//
// Synthesis: 2 constraint modules in parallel + AND gate

module compose_product_2d (
    input  logic        c1_result,
    input  logic        c2_result,
    output logic        result
);

    assign result = c1_result && c2_result;

endmodule
