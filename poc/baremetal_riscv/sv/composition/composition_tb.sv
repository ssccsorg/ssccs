// SSCCS Composition Testbench
//
// Standalone verification of composition modules:
// - compose_union:       C1 ∨ C2 (OR reduction)
// - compose_intersect:   C1 ∧ C2 (AND reduction)
// - compose_product_2d:  C1(x) ∧ C2(y)
// - compose_pipeline:    A output → B input (operator-level)
// - proj_mul:            multiplication projector
// - proj_div:            division projector with zero-guard

`include "_golden_anchors.svh"

module composition_tb;

    // DUT: union (2-constraint default + 4-constraint param)
    wire union_2_result;
    wire union_4_result;

    // DUT: intersect (2-constraint default + 5-constraint param)
    wire intersect_2_result;
    wire intersect_5_result;

    // DUT: product_2d
    wire product_result;

    // DUT: pipeline, mul, div
    wire [63:0] pipe_result;
    wire [63:0] mul_result;
    wire [63:0] div_result;

    // Pipeline clock/reset
    reg clk;
    reg rst_n;

    // Exhaustive 2-bit inputs
    logic [1:0] c2;

    // Multi-constraint test vectors
    logic [3:0] c4;  // 4 constraints
    logic [4:0] c5;  // 5 constraints

    // Instantiate composition modules

    compose_union #(.NUM_CONSTRAINTS(2)) u_union_2 (
        .constraint_results(c2),
        .result(union_2_result)
    );

    compose_union #(.NUM_CONSTRAINTS(4)) u_union_4 (
        .constraint_results(c4),
        .result(union_4_result)
    );

    compose_intersect #(.NUM_CONSTRAINTS(2)) u_intersect_2 (
        .constraint_results(c2),
        .result(intersect_2_result)
    );

    compose_intersect #(.NUM_CONSTRAINTS(5)) u_intersect_5 (
        .constraint_results(c5),
        .result(intersect_5_result)
    );

    wire [63:0] sum_result;

    proj_sum2d u_pipe_source (
        .coord_a(64'd7),
        .coord_b(64'd6),
        .result(sum_result)
    );

    compose_pipeline u_pipe (
        .clk(clk),
        .rst_n(rst_n),
        .intermediate_in(sum_result),
        .piped_out(pipe_result),
        .result()
    );

    proj_mul u_mul (
        .coord_a(64'd7),
        .coord_b(64'd6),
        .result(mul_result)
    );

    proj_div u_div (
        .coord_a(64'd42),
        .coord_b(64'd6),
        .result(div_result)
    );

    compose_product_2d u_product (
        .c1_result(c2[1]),
        .c2_result(c2[0]),
        .result(product_result)
    );

    // Clock generator
    initial begin
        clk = 0;
        rst_n = 0;
        #2 rst_n = 1;
        forever #1 clk = ~clk;
    end

    // Test sequence
    initial begin
        #1;

        $display("=== SSCCS Composition Module Verification ===");
        $display("");

        // ---- union 2-constraint ----
        $display("-- compose_union (NUM_CONSTRAINTS=2) --");

        c2 = 2'b00; #1;
        assert(union_2_result == 1'b0) else $error("union(0,0): expected 0");
        $display("  union(0,0) = %0b  PASS", union_2_result);

        c2 = 2'b01; #1;
        assert(union_2_result == 1'b1) else $error("union(0,1): expected 1");
        $display("  union(0,1) = %0b  PASS", union_2_result);

        c2 = 2'b10; #1;
        assert(union_2_result == 1'b1) else $error("union(1,0): expected 1");
        $display("  union(1,0) = %0b  PASS", union_2_result);

        c2 = 2'b11; #1;
        assert(union_2_result == 1'b1) else $error("union(1,1): expected 1");
        $display("  union(1,1) = %0b  PASS", union_2_result);

        // ---- union 4-constraint ----
        $display("");
        $display("-- compose_union (NUM_CONSTRAINTS=4) --");

        c4 = 4'b0000; #1;
        assert(union_4_result == 1'b0) else $error("union(0,0,0,0): expected 0");
        $display("  union(0,0,0,0) = %0b  PASS", union_4_result);

        c4 = 4'b0001; #1;
        assert(union_4_result == 1'b1) else $error("union(0,0,0,1): expected 1");
        $display("  union(0,0,0,1) = %0b  PASS", union_4_result);

        c4 = 4'b1010; #1;
        assert(union_4_result == 1'b1) else $error("union(1,0,1,0): expected 1");
        $display("  union(1,0,1,0) = %0b  PASS", union_4_result);

        c4 = 4'b1111; #1;
        assert(union_4_result == 1'b1) else $error("union(1,1,1,1): expected 1");
        $display("  union(1,1,1,1) = %0b  PASS", union_4_result);

        // ---- intersect 2-constraint ----
        $display("");
        $display("-- compose_intersect (NUM_CONSTRAINTS=2) --");

        c2 = 2'b00; #1;
        assert(intersect_2_result == 1'b0) else $error("intersect(0,0): expected 0");
        $display("  intersect(0,0) = %0b  PASS", intersect_2_result);

        c2 = 2'b01; #1;
        assert(intersect_2_result == 1'b0) else $error("intersect(0,1): expected 0");
        $display("  intersect(0,1) = %0b  PASS", intersect_2_result);

        c2 = 2'b10; #1;
        assert(intersect_2_result == 1'b0) else $error("intersect(1,0): expected 0");
        $display("  intersect(1,0) = %0b  PASS", intersect_2_result);

        c2 = 2'b11; #1;
        assert(intersect_2_result == 1'b1) else $error("intersect(1,1): expected 1");
        $display("  intersect(1,1) = %0b  PASS", intersect_2_result);

        // ---- intersect 5-constraint ----
        $display("");
        $display("-- compose_intersect (NUM_CONSTRAINTS=5) --");

        c5 = 5'b11111; #1;
        assert(intersect_5_result == 1'b1) else $error("intersect(all 1s): expected 1");
        $display("  intersect(1,1,1,1,1) = %0b  PASS", intersect_5_result);

        c5 = 5'b11110; #1;
        assert(intersect_5_result == 1'b0) else $error("intersect(1,1,1,1,0): expected 0");
        $display("  intersect(1,1,1,1,0) = %0b  PASS", intersect_5_result);

        c5 = 5'b10101; #1;
        assert(intersect_5_result == 1'b0) else $error("intersect(1,0,1,0,1): expected 0");
        $display("  intersect(1,0,1,0,1) = %0b  PASS", intersect_5_result);

        // ---- product_2d ----
        $display("");
        $display("-- compose_product_2d --");

        c2 = 2'b00; #1;
        assert(product_result == 1'b0) else $error("product(0,0): expected 0");
        $display("  product(0,0) = %0b  PASS", product_result);

        c2 = 2'b01; #1;
        assert(product_result == 1'b0) else $error("product(0,1): expected 0");
        $display("  product(0,1) = %0b  PASS", product_result);

        c2 = 2'b10; #1;
        assert(product_result == 1'b0) else $error("product(1,0): expected 0");
        $display("  product(1,0) = %0b  PASS", product_result);

        c2 = 2'b11; #1;
        assert(product_result == 1'b1) else $error("product(1,1): expected 1");
        $display("  product(1,1) = %0b  PASS", product_result);

        // ---- pipeline + projector tests ----
        #1;
        $display("");
        $display("-- compose_pipeline / proj_mul / proj_div --");

        assert(mul_result == 64'd42) else $error("proj_mul(7,6): expected 42");
        $display("  proj_mul(7,6) = %0d  PASS", mul_result);

        assert(div_result == 64'd7) else $error("proj_div(42,6): expected 7");
        $display("  proj_div(42,6) = %0d  PASS", div_result);

        // proj_sum2d(7,6) = 13 (combinational, feeds compose_pipeline.intermediate_in)
        #1;
        assert(sum_result == 64'd13) else $error("proj_sum2d(7,6): expected 13");
        $display("  proj_sum2d(7,6) = %0d  PASS", sum_result);

        // After clock edge, pipeline register latches sum_result
        @(posedge clk); #1;
        assert(pipe_result == 64'd13) else $error("pipeline reg: expected 13");
        $display("  compose_pipeline(13) = %0d  PASS", pipe_result);

        $display("");
        $display("=== Composition Verification: ALL PASSED ===");
        $finish;
    end

endmodule
