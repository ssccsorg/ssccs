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
// SSCCS Projector: Division (with zero-guard)
// proj_div(a, b) → a / b
//
// nex-calc OpType::Div: if b == 0 → CalcOpError::DivisionByZero
//
// Hardware: returns 0 on division by zero (REJECT sentinel path).
// The caller should check for zero divisor separately if error
// propagation is needed.

module proj_div (
    input  logic [63:0] coord_a,
    input  logic [63:0] coord_b,
    output logic [63:0] result
);

    assign result = (coord_b == 64'd0) ? 64'd0 : coord_a / coord_b;

endmodule
