// SSCCS Composition: Pipeline (Compose)
// P(x, y, z) = B(A(x, y), z)
//
// Operator-level sequential composition: the output of Projector A
// becomes the input to Projector B. This is NOT constraint-level
// filtering (Union/Intersection/Product), but operator chaining.
//
// Concept proven by nex-calc (nexus PR #143):
//   calc.op(OpType::Add, &a, &b) → resolve → intermediate Fact → calc.op(OpType::Mul, ...) → resolve → result
//
// Hardware: pipeline register between two projector stages
//   [Projector A] → [intermediate_in] → [pipeline reg] → [piped_out] → [Projector B] → result
//
// Usage:
//   compose_pipeline u_pipe (.clk, .rst_n, .intermediate_in(sum_result), .piped_out(piped), .result());
//   proj_sum2d  u_a (.coord_a(x), .coord_b(y), .result(sum_result));
//   proj_mul    u_b (.coord_a(piped), .coord_b(z), .result(final_result));

module compose_pipeline (
    input  logic        clk,
    input  logic        rst_n,
    input  logic [63:0] intermediate_in,  // Projector A's output (driven externally)
    output logic [63:0] piped_out,        // Pipeline register output (to Projector B)
    output logic [63:0] result            // Same as piped_out (convenience alias)
);

    logic [63:0] stage_reg;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            stage_reg <= 64'd0;
        else
            stage_reg <= intermediate_in;
    end

    assign piped_out = stage_reg;
    assign result    = stage_reg;

endmodule
