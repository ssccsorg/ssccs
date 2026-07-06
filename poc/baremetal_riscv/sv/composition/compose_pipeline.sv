// SSCCS Composition: Pipeline (Compose)
// P(x,y) = B(A(x, y_a), y_b)
//
// Operator-level sequential composition: the output of Projector A
// becomes the input to Projector B. This is NOT constraint-level
// filtering (Union/Intersection/Product), but operator chaining.
//
// Concept proven by nex-calc (nexus PR #143):
//   resolve(A) → intermediate Fact → resolve(B) → result Fact
//
// Hardware mapping: Pipeline register
//   [coord] → [Projector A] → [reg] → [Projector B] → [result]
//
// This is distinct from compose_union (C₁ ∨ C₂) and compose_intersect
// (C₁ ∧ C₂), which check constraint admissibility in parallel.
// compose_pipeline chains projectors sequentially.

module compose_pipeline (
    input  logic clk,
    input  logic rst_n,
    input  logic [63:0] coord_a,
    input  logic [63:0] coord_b,
    output logic [63:0] result
);

    // Stage 1: Projector A
    logic [63:0] intermediate;

    // Stage 2: Projector B uses intermediate as one operand
    // The caller wires the appropriate projector modules externally
    // and connects their inputs/outputs through the pipeline stage registers.

    // Pipeline register
    logic [63:0] stage_reg;
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            stage_reg <= 64'd0;
        else
            stage_reg <= intermediate;
    end

    // The actual projector wiring is done by the instantiating module.
    // This module provides the pipeline stage structure; the caller
    // instantiates proj_x and proj_y modules and connects them through
    // this pipeline's ports.
    //
    // Example instantiation:
    //   compose_pipeline u_pipe (.clk, .rst_n, .coord_a, .coord_b, .result);
    //   proj_sum2d u_a (.coord_a(data_x), .coord_b(data_y), .result(u_pipe.intermediate));
    //   proj_mul  u_b (.coord_a(u_pipe.stage_reg), .coord_b(data_z), .result(u_pipe.result));

endmodule
