// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Research in progress. Read, check, and cite it. See LICENSE at the root of
// this proof of concept before copying it into another work.
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
