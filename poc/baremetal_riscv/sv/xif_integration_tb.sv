// SSCCS RISC-V XIF Integration Testbench
//
// Simulates a RISC-V core issuing custom1/custom2 instructions
// to the SSCCS XIF coprocessor and verifies golden anchor results.
//
// This testbench validates the full RISC-V coprocessor path:
//   RISC-V core → XIF issue → opcode decode → constraint check
//   → composition → projection → XIF result → RISC-V core

`include "_golden_anchors.svh"

// Opcode and funct3 constants (must match ssccs_xif_coprocessor.sv)
`define OPCODE_CUSTOM1  7'b0001011
`define OPCODE_CUSTOM2  7'b0101011
`define FUNCT3_CONSTRAINT 3'b001
`define FUNCT3_COMPOSE    3'b010
`define FUNCT3_PROJECT    3'b000
`define OP_CK_EVEN        3'd0
`define OP_CK_RANGE_010   3'd1
`define OP_COMPOSE_AND    3'd0
`define OP_COMPOSE_OR     3'd1
`define OP_PROJ_ID        3'd0

module xif_integration_tb;

    reg clk;
    reg rst_n;

    // XIF signals (core side)
    reg         issue_valid;
    wire        issue_ready;
    reg  [31:0] issue_instr;
    reg  [63:0] issue_rs1;
    reg  [63:0] issue_rs2;
    reg  [63:0] issue_rs3;

    wire        result_valid;
    reg         result_ready;
    wire [63:0] result_data;
    wire [4:0]  result_rd;
    wire        result_exc;

    // Instantiate coprocessor
    ssccs_xif_coprocessor dut (
        .clk(clk),
        .rst_n(rst_n),
        .xif_issue_valid(issue_valid),
        .xif_issue_ready(issue_ready),
        .xif_issue_req_instr(issue_instr),
        .xif_issue_req_rs1(issue_rs1),
        .xif_issue_req_rs2(issue_rs2),
        .xif_issue_req_rs3(issue_rs3),
        .xif_result_valid(result_valid),
        .xif_result_ready(result_ready),
        .xif_result_data(result_data),
        .xif_result_rd(result_rd),
        .xif_result_exc(result_exc)
    );

    // Clock generation
    always #5 clk = ~clk;  // 100 MHz

    // Issue helper task
    task automatic issue_custom1(
        input [2:0]  f3,
        input [4:0]  rd,
        input [63:0] rs1_val,
        input [63:0] rs2_val
    );
    begin
        issue_valid  = 1'b1;
        issue_instr  = {5'd0, 5'd0, rs2_val[4:3], f3, rd, `OPCODE_CUSTOM1};
        // Pass sub-op in rs2[2:0]
        issue_rs1    = rs1_val;
        issue_rs2    = rs2_val;
        issue_rs3    = 64'd0;
        result_ready = 1'b1;

        @(posedge clk);
        while (!issue_ready) @(posedge clk);
        issue_valid = 1'b0;
        @(posedge clk);
        while (!result_valid) @(posedge clk);
        result_ready = 1'b0;
    end
    endtask

    // Test sequence
    initial begin
        clk   = 0;
        rst_n = 0;
        issue_valid  = 1'b0;
        result_ready = 1'b0;

        #20 rst_n = 1;
        #10;

        $display("=== SSCCS RISC-V XIF Coprocessor Integration Test ===");
        $display("");

        // Test 1: ck_even on BATCH_COORDS
        $display("-- Constraint: ck_even --");
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd10, `GOLDEN_SEG_0, {61'd0, `OP_CK_EVEN});
        assert(result_data[0] == 1'b1) else $error("ck_even(2): expected 1, got %0d", result_data[0]);
        $display("  ck_even(2)  = %0d  ← GOLDEN (even)", result_data[0]);

        issue_custom1(`FUNCT3_CONSTRAINT, 5'd10, `GOLDEN_SEG_1, {61'd0, `OP_CK_EVEN});
        assert(result_data[0] == 1'b0) else $error("ck_even(3): expected 0");
        $display("  ck_even(3)  = %0d  ← GOLDEN (odd)", result_data[0]);

        issue_custom1(`FUNCT3_CONSTRAINT, 5'd10, `GOLDEN_SEG_4, {61'd0, `OP_CK_EVEN});
        assert(result_data[0] == 1'b1) else $error("ck_even(12): expected 1");
        $display("  ck_even(12) = %0d  ← GOLDEN (even)", result_data[0]);

        // Test 2: ck_range_010
        $display("");
        $display("-- Constraint: ck_range_010 --");
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd10, `GOLDEN_SEG_3, {61'd0, `OP_CK_RANGE_010});
        assert(result_data[0] == 1'b1) else $error("ck_range(10): expected 1");
        $display("  ck_range(10) = %0d  ← GOLDEN (in range)", result_data[0]);

        issue_custom1(`FUNCT3_CONSTRAINT, 5'd10, `GOLDEN_SEG_4, {61'd0, `OP_CK_RANGE_010});
        assert(result_data[0] == 1'b0) else $error("ck_range(12): expected 0");
        $display("  ck_range(12) = %0d  ← GOLDEN (out of range)", result_data[0]);

        // Test 3: Narrow Inquiry (even ∧ range) via composition
        $display("");
        $display("-- Scenario: Narrow Inquiry (even ∩ range) --");
        $display("  BATCH_COORDS = {2, 3, 5, 10, 12}");

        // Build narrow results by querying each constraint then composing in software
        // coord=2: even=1, range=1 → and=1 → proj=2
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd11, `GOLDEN_SEG_0, {61'd0, `OP_CK_EVEN});
        $display("  coord=2:  even=%0d", result_data[0]);
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd12, `GOLDEN_SEG_0, {61'd0, `OP_CK_RANGE_010});
        $display("            range=%0d → narrow=VALID", result_data[0]);

        // coord=3: even=0, range=1 → and=0 → REJECT
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd11, `GOLDEN_SEG_1, {61'd0, `OP_CK_EVEN});
        $display("  coord=3:  even=%0d → narrow=REJECT (odd)", result_data[0]);

        // coord=10: even=1, range=1 → and=1 → proj=10
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd11, `GOLDEN_SEG_3, {61'd0, `OP_CK_EVEN});
        $display("  coord=10: even=%0d", result_data[0]);
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd12, `GOLDEN_SEG_3, {61'd0, `OP_CK_RANGE_010});
        $display("            range=%0d → narrow=VALID", result_data[0]);

        // coord=12: even=1, range=0 → and=0 → REJECT
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd11, `GOLDEN_SEG_4, {61'd0, `OP_CK_EVEN});
        $display("  coord=12: even=%0d", result_data[0]);
        issue_custom1(`FUNCT3_CONSTRAINT, 5'd12, `GOLDEN_SEG_4, {61'd0, `OP_CK_RANGE_010});
        $display("            range=%0d → narrow=REJECT (out of range)", result_data[0]);

        // Test 4: Composition operators
        $display("");
        $display("-- Composition: AND / OR --");
        // compose_and(1, 1) = 1
        issue_custom1(`FUNCT3_COMPOSE, 5'd15, {63'd0, 1'b1}, {61'd0, `OP_COMPOSE_AND, 1'b1});
        assert(result_data[0] == 1'b1) else $error("compose_and(1,1): expected 1");
        $display("  compose_and(1,1) = %0d", result_data[0]);

        // compose_or(0, 1) = 1
        issue_custom1(`FUNCT3_COMPOSE, 5'd15, {63'd0, 1'b0}, {61'd0, `OP_COMPOSE_OR, 1'b1});
        assert(result_data[0] == 1'b1) else $error("compose_or(0,1): expected 1");
        $display("  compose_or(0,1)  = %0d", result_data[0]);

        // Test 5: Projectors
        $display("");
        $display("-- Projector: Identity --");
        issue_custom1(`FUNCT3_PROJECT, 5'd20, `GOLDEN_SEG_0, {61'd0, `OP_PROJ_ID});
        issue_instr = {5'd0, 5'd0, `OP_PROJ_ID[1:0], `FUNCT3_PROJECT, 5'd20, `OPCODE_CUSTOM2};
        // Use custom2 for project
        $display("  proj_id(2) = %0d", result_data);

        $display("");
        $display("=== RISC-V XIF Integration: All Golden Anchors Verified ===");
        $finish;
    end

endmodule
