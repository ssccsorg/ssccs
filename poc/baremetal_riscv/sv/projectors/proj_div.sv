// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
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
