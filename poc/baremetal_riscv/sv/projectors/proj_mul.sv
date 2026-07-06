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
