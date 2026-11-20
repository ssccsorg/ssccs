// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
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

    // Signed order anchors: a negative coordinate against negative bounds, where an unsigned compare disagrees.
    wire signed_range_lo;
    wire signed_range_hi;
    wire signed_gt_a;
    wire signed_gt_b;

    ck_range u_signed_range_lo (
        .coord(-64'sd2), .min_val(-64'sd10), .max_val(64'sd10), .result(signed_range_lo)
    );

    ck_range u_signed_range_hi (
        .coord(-64'sd2), .min_val(64'sd0), .max_val(64'sd10), .result(signed_range_hi)
    );

    ck_gt u_signed_gt_a (
        .coord(-64'sd2), .threshold(-64'sd5), .result(signed_gt_a)
    );

    ck_gt u_signed_gt_b (
        .coord(-64'sd5), .threshold(-64'sd2), .result(signed_gt_b)
    );

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
                .constraint_result(narrow_constraint[i]),
                .projection(projection[i]),
                .result(result_narrow[i]),
                .valid(valid_narrow[i])
            );

            observe observe_broad (
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
        // The order the space uses is i64's, so a negative bound is inside its own range.
        $display("");
        $display("Signed order (negative coordinate, negative bounds):");
        assert (signed_range_lo == `GOLDEN_SIGNED_RANGE_0) else
            $error("SIGNED_RANGE[0] FAIL: got %0d, expected %0d", signed_range_lo, `GOLDEN_SIGNED_RANGE_0);
        $display("  range(-2, -10, 10) = %0d", signed_range_lo);

        assert (signed_range_hi == `GOLDEN_SIGNED_RANGE_1) else
            $error("SIGNED_RANGE[1] FAIL: got %0d, expected %0d", signed_range_hi, `GOLDEN_SIGNED_RANGE_1);
        $display("  range(-2,   0, 10) = %0d", signed_range_hi);

        assert (signed_gt_a == `GOLDEN_SIGNED_GT_0) else
            $error("SIGNED_GT[0] FAIL: got %0d, expected %0d", signed_gt_a, `GOLDEN_SIGNED_GT_0);
        $display("  gt(-2, -5) = %0d", signed_gt_a);

        assert (signed_gt_b == `GOLDEN_SIGNED_GT_1) else
            $error("SIGNED_GT[1] FAIL: got %0d, expected %0d", signed_gt_b, `GOLDEN_SIGNED_GT_1);
        $display("  gt(-5, -2) = %0d", signed_gt_b);

        $display("=== All Golden Anchors Verified ===");
        $finish;
    end

endmodule
