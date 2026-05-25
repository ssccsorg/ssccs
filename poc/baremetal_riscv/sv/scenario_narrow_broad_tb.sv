// SSCCS Scenario: Narrow vs Broad Inquiry
// Golden Bridge Testbench — Rust ↔ RISC-V asm ↔ SystemVerilog
//
// BATCH_COORDS = {2, 3, 5, 10, 12}
//
// Narrow (∩): even ∧ range[0,10]
//   Expected: 2, REJECT, REJECT, 10, REJECT
//
// Broad (∪):  even ∨ range[0,10]
//   Expected: 2, 3, 5, 10, 12
//
// This testbench instantiates the same logic as observe_full.S
// and asserts against GOLDEN_NARROW / GOLDEN_BROAD anchors.

`include "_golden_anchors.svh"

module scenario_narrow_broad_tb;

    // DUT instantiations

    // Individual constraints
    wire ck_even_result [0:4];
    wire ck_range_result [0:4];

    // Identity projector: passes coord through as-is
    wire logic [63:0] projection [0:4];
    wire logic        valid_narrow [0:4];
    wire logic        valid_broad [0:4];
    wire logic [63:0] result_narrow [0:4];
    wire logic [63:0] result_broad [0:4];

    // Composition results
    wire logic narrow_constraint [0:4];
    wire logic broad_constraint [0:4];

    genvar i;

    // 5 test coordinates
    localparam logic [63:0] SEG_0 = `GOLDEN_SEG_0;   // 2
    localparam logic [63:0] SEG_1 = `GOLDEN_SEG_1;   // 3
    localparam logic [63:0] SEG_2 = `GOLDEN_SEG_2;   // 5
    localparam logic [63:0] SEG_3 = `GOLDEN_SEG_3;   // 10
    localparam logic [63:0] SEG_4 = `GOLDEN_SEG_4;   // 12

    logic [63:0] coords [0:4];

    assign coords[0] = SEG_0;
    assign coords[1] = SEG_1;
    assign coords[2] = SEG_2;
    assign coords[3] = SEG_3;
    assign coords[4] = SEG_4;

    generate
        for (i = 0; i < 5; i = i + 1) begin : gen_constraints

            ck_even ck_even_inst (
                .coord(coords[i]),
                .result(ck_even_result[i])
            );

            ck_range_010 ck_range_inst (
                .coord(coords[i]),
                .result(ck_range_result[i])
            );

            // Narrow: even ∧ range
            assign narrow_constraint[i] = ck_even_result[i] && ck_range_result[i];

            // Broad: even ∨ range
            assign broad_constraint[i]   = ck_even_result[i] || ck_range_result[i];

            // Identity projector
            assign projection[i] = coords[i];

            // Observation pipeline
            observe observe_narrow (
                .coord(coords[i]),
                .constraint_result(narrow_constraint[i]),
                .projection(projection[i]),
                .result(result_narrow[i]),
                .valid(valid_narrow[i])
            );

            observe observe_broad (
                .coord(coords[i]),
                .constraint_result(broad_constraint[i]),
                .projection(projection[i]),
                .result(result_broad[i]),
                .valid(valid_broad[i])
            );

        end
    endgenerate

    // Golden anchor assertions
    initial begin
        #1;  // allow combinational logic to settle

        $display("=== SSCCS Scenario: Narrow vs Broad Inquiry ===");
        $display("");

        // Narrow: even ∧ range[0,10]
        $display("Narrow (even ∩ range[0,10]):");
        assert (result_narrow[0] == `GOLDEN_NARROW_0) else
            $error("NARROW[0] FAIL: got %0d, expected %0d", result_narrow[0], `GOLDEN_NARROW_0);
        $display("  coord=2  → VALID, result=%0d", result_narrow[0]);

        assert (result_narrow[1] == `GOLDEN_NARROW_1) else
            $error("NARROW[1] FAIL: got 0x%0h, expected REJECT", result_narrow[1]);
        $display("  coord=3  → REJECT (odd)");

        assert (result_narrow[2] == `GOLDEN_NARROW_2) else
            $error("NARROW[2] FAIL: got 0x%0h, expected REJECT", result_narrow[2]);
        $display("  coord=5  → REJECT (odd)");

        assert (result_narrow[3] == `GOLDEN_NARROW_3) else
            $error("NARROW[3] FAIL: got %0d, expected %0d", result_narrow[3], `GOLDEN_NARROW_3);
        $display("  coord=10 → VALID, result=%0d", result_narrow[3]);

        assert (result_narrow[4] == `GOLDEN_NARROW_4) else
            $error("NARROW[4] FAIL: got 0x%0h, expected REJECT", result_narrow[4]);
        $display("  coord=12 → REJECT (out of range)");

        $display("");

        // Broad: even ∨ range[0,10]
        $display("Broad (even ∪ range[0,10]):");
        assert (result_broad[0] == `GOLDEN_BROAD_0) else
            $error("BROAD[0] FAIL: got %0d, expected %0d", result_broad[0], `GOLDEN_BROAD_0);
        $display("  coord=2  → VALID, result=%0d", result_broad[0]);

        assert (result_broad[1] == `GOLDEN_BROAD_1) else
            $error("BROAD[1] FAIL: got %0d, expected %0d", result_broad[1], `GOLDEN_BROAD_1);
        $display("  coord=3  → VALID, result=%0d (in range)", result_broad[1]);

        assert (result_broad[2] == `GOLDEN_BROAD_2) else
            $error("BROAD[2] FAIL: got %0d, expected %0d", result_broad[2], `GOLDEN_BROAD_2);
        $display("  coord=5  → VALID, result=%0d (in range)", result_broad[2]);

        assert (result_broad[3] == `GOLDEN_BROAD_3) else
            $error("BROAD[3] FAIL: got %0d, expected %0d", result_broad[3], `GOLDEN_BROAD_3);
        $display("  coord=10 → VALID, result=%0d (in range)", result_broad[3]);

        assert (result_broad[4] == `GOLDEN_BROAD_4) else
            $error("BROAD[4] FAIL: got %0d, expected %0d", result_broad[4], `GOLDEN_BROAD_4);
        $display("  coord=12 → VALID, result=%0d (even)", result_broad[4]);

        $display("");
        $display("=== All Golden Anchors Verified ===");
        $finish;
    end

endmodule
