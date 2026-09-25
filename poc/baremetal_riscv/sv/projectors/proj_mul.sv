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
// SSCCS Projector: Multiplication
// proj_mul(a, b) → a * b
//
// nex-calc OpType::Mul: Fact(lhs) * Fact(rhs) → Fact(result)
//
// Synthesis: DSP slice or LUT-based multiplier depending on
// target frequency and area constraints.

module proj_mul (
    input  logic [63:0] coord_a,
    input  logic [63:0] coord_b,
    output logic [63:0] result
);

    assign result = coord_a * coord_b;

endmodule
