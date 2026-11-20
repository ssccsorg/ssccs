// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// The scenario's anchors, compared one line at a time on the die. A coordinate is the space's own i64,
// because the order the tables assume is signed.
//
// The POC states its anchors across the assembly, the SystemVerilog and the Rust fallback, and this is the same
// check on a fourth substrate. Each line of the ROM carries one coordinate and the two results the inquiry
// expects for it, and the die runs the kinds the inquiry names and observe over that coordinate. The verdict is a
// comparison per line, so a single wrong coordinate is the same size as the whole table.
//
// The ROM is generated from sv/_golden_anchors.svh by anchor_rom.py, because a table transcribed by hand is a
// table the anchors do not have to hold. The paths are fixed for synthesis: $readmemh resolves against the
// directory the flow runs in, which is this board's folder. A simulation takes them from plusargs instead, so one
// build checks the anchors and a table with two expectations exchanged.
//
//   stage[0] -> N4, iCELink PA0, driven by the host
//   stage[1] -> J5, iCELink PA1, driven by the host
//   pin_match -> H5, iCELink PA13, read by the host
//   led_green -> A11, led_blue -> A12, led_red -> B11
//
// pin_match is set only when a full pass finished with no line disagreeing. COUNT comes from the flow, which
// reads it from the same table, so the die cannot be told a length its ROM does not have.

`include "_units.svh"

module ssccs_anchor_board #(
    parameter integer COUNT = 0
) (
    input  wire       clk_in,
    input  wire [1:0] stage,
    output wire       pin_match,
    output wire       led_red,
    output wire       led_green,
    output wire       led_blue
);

    // The sentinel observe() emits for a rejected coordinate: i64::MIN, as the assembly and the Rust fallback write it.
    localparam [63:0] REJECT = 64'h8000000000000000;

    // The board's own 25 MHz crystal is the clock. Five lines need no PLL, and a clock the flow cannot constrain is
    // a number nobody measured.
    wire clk = clk_in;

    localparam integer ADDR_BITS = (COUNT > 1) ? $clog2(COUNT) : 1;
    // The ROM is addressed by an ADDR_BITS counter, so its depth is that whole space. A depth of COUNT that is not a
    // power of two leaves the mapping to round, and a memory that comes up short compares the missing lines against
    // nothing. COUNT still governs the wrap, and no address at or above it is read.
    localparam integer DEPTH = 1 << ADDR_BITS;

    reg [63:0] coord [0:DEPTH-1];
    reg [63:0] narrow [0:DEPTH-1];
    reg [63:0] broad [0:DEPTH-1];
    // One descriptor says what those two tables are compared against, and eight words carry the bounds: two
    // operands for each of the four slots. `program` is a keyword in SystemVerilog, so the file is the inquiry.
    reg [63:0] inquiry [0:8];

`ifdef SIM
    reg [1023:0] coord_file;
    reg [1023:0] narrow_file;
    reg [1023:0] broad_file;
    reg [1023:0] inquiry_file;

    initial begin
        if (!$value$plusargs("coord=%s", coord_file)) coord_file = "out/anchor_coord.hex";
        if (!$value$plusargs("narrow=%s", narrow_file)) narrow_file = "out/anchor_narrow.hex";
        if (!$value$plusargs("broad=%s", broad_file)) broad_file = "out/anchor_broad.hex";
        if (!$value$plusargs("inquiry=%s", inquiry_file)) inquiry_file = "out/anchor_inquiry.hex";
        $readmemh(coord_file, coord);
        $readmemh(narrow_file, narrow);
        $readmemh(broad_file, broad);
        $readmemh(inquiry_file, inquiry);
    end
`else
    initial begin
        $readmemh("out/anchor_coord.hex", coord);
        $readmemh("out/anchor_narrow.hex", narrow);
        $readmemh("out/anchor_broad.hex", broad);
        $readmemh("out/anchor_inquiry.hex", inquiry);
    end
`endif

    reg [ADDR_BITS-1:0] addr = 0;

    always @(posedge clk)
        addr <= (addr == COUNT - 1) ? {ADDR_BITS{1'b0}} : addr + 1'b1;

    // One synchronous read stage: the memory is a block RAM rather than distributed logic, and the coordinate,
    // the projection and both expectations arrive together so the comparison needs no second delay chain.
    reg [63:0] coord_r = 0;
    reg [63:0] narrow_r = 0;
    reg [63:0] broad_r = 0;

    always @(posedge clk) begin
        coord_r  <= coord[addr];
        narrow_r <= narrow[addr];
        broad_r  <= broad[addr];
    end

    wire [63:0] point = coord_r;

    wire even;

    ck_even u_even (
        .coord(point),
        .result(even)
    );

    // The kinds are the core's (`sv/_units.svh`) and the bounds are the inquiry's, so a constraint is a kind and two
    // numbers. A kind this image does not carry answers zero, so an inquiry naming one fails rather than passes.
    wire [2:0] narrow_a = inquiry[0][13:11];
    wire [2:0] narrow_b = inquiry[0][10:8];
    wire       narrow_op = inquiry[0][7];
    wire [2:0] broad_a = inquiry[0][6:4];
    wire [2:0] broad_b = inquiry[0][3:1];
    wire       broad_op = inquiry[0][0];

    // One instance of each bound kind per slot, carrying that slot's operands. The board supplies the units and
    // the table supplies the bounds, so this file names no scenario.
    wire na_range, na_eq, na_gt;
    wire nb_range, nb_eq, nb_gt;
    wire ba_range, ba_eq, ba_gt;
    wire bb_range, bb_eq, bb_gt;

    ck_range u_na_range (.coord(point), .min_val(inquiry[1]), .max_val(inquiry[2]), .result(na_range));
    ck_eq    u_na_eq    (.coord(point), .target(inquiry[1]),                         .result(na_eq));
    ck_gt    u_na_gt    (.coord(point), .threshold(inquiry[1]),                      .result(na_gt));

    ck_range u_nb_range (.coord(point), .min_val(inquiry[3]), .max_val(inquiry[4]), .result(nb_range));
    ck_eq    u_nb_eq    (.coord(point), .target(inquiry[3]),                         .result(nb_eq));
    ck_gt    u_nb_gt    (.coord(point), .threshold(inquiry[3]),                      .result(nb_gt));

    ck_range u_ba_range (.coord(point), .min_val(inquiry[5]), .max_val(inquiry[6]), .result(ba_range));
    ck_eq    u_ba_eq    (.coord(point), .target(inquiry[5]),                         .result(ba_eq));
    ck_gt    u_ba_gt    (.coord(point), .threshold(inquiry[5]),                      .result(ba_gt));

    ck_range u_bb_range (.coord(point), .min_val(inquiry[7]), .max_val(inquiry[8]), .result(bb_range));
    ck_eq    u_bb_eq    (.coord(point), .target(inquiry[7]),                         .result(bb_eq));
    ck_gt    u_bb_gt    (.coord(point), .threshold(inquiry[7]),                      .result(bb_gt));

    wire narrow_pick_a =
        (narrow_a == `UNIT_EVEN) ? even
        : (narrow_a == `UNIT_RANGE) ? na_range
        : (narrow_a == `UNIT_EQ) ? na_eq
        : (narrow_a == `UNIT_GT) ? na_gt
        : 1'b0;
    wire narrow_pick_b =
        (narrow_b == `UNIT_EVEN) ? even
        : (narrow_b == `UNIT_RANGE) ? nb_range
        : (narrow_b == `UNIT_EQ) ? nb_eq
        : (narrow_b == `UNIT_GT) ? nb_gt
        : 1'b0;
    wire broad_pick_a =
        (broad_a == `UNIT_EVEN) ? even
        : (broad_a == `UNIT_RANGE) ? ba_range
        : (broad_a == `UNIT_EQ) ? ba_eq
        : (broad_a == `UNIT_GT) ? ba_gt
        : 1'b0;
    wire broad_pick_b =
        (broad_b == `UNIT_EVEN) ? even
        : (broad_b == `UNIT_RANGE) ? bb_range
        : (broad_b == `UNIT_EQ) ? bb_eq
        : (broad_b == `UNIT_GT) ? bb_gt
        : 1'b0;

    wire narrow_constraint = (narrow_op == `COMPOSE_OR) ? (narrow_pick_a || narrow_pick_b) : (narrow_pick_a && narrow_pick_b);
    wire broad_constraint  = (broad_op == `COMPOSE_OR)  ? (broad_pick_a || broad_pick_b)  : (broad_pick_a && broad_pick_b);

    wire [63:0] narrow_result;
    wire [63:0] broad_result;
    wire narrow_valid;
    wire broad_valid;

    observe u_narrow (
        .constraint_result(narrow_constraint),
        .projection(point),
        .result(narrow_result),
        .valid(narrow_valid)
    );

    observe u_broad (
        .constraint_result(broad_constraint),
        .projection(point),
        .result(broad_result),
        .valid(broad_valid)
    );

    // A line that expects the sentinel expects a rejection, and a line that expects a value expects both a valid
    // observation and that value. Either expectation disagreeing is a mismatch.
    wire narrow_pass = (narrow_r == REJECT) ? ~narrow_valid : (narrow_valid && (narrow_result == narrow_r));
    wire broad_pass  = (broad_r == REJECT) ? ~broad_valid : (broad_valid && (broad_result == broad_r));

    // Two clocks of fill: the first read has not reached the comparison yet, and an uninitialised register read as
    // a mismatch would make the image refuse the table it was given.
    reg [1:0] fill = 2'b00;

    always @(posedge clk)
        fill <= {fill[0], 1'b1};

    wire warm = fill[1];

    reg [31:0] mismatches = 32'd0;
    reg [ADDR_BITS-1:0] seen = 0;
    reg matched = 1'b0;

    wire [31:0] mismatch_next = (narrow_pass && broad_pass) ? mismatches : mismatches + 32'd1;

    always @(posedge clk) begin
        if (warm) begin
            if (seen == COUNT - 1) begin
                // This line closes the pass, so the next count holds the whole table's total. Neither is cleared on
                // the closing edge: a pass that found a mismatch has to keep saying so.
                matched <= (mismatch_next == 32'd0);
                mismatches <= 32'd0;
                seen <= {ADDR_BITS{1'b0}};
            end else begin
                mismatches <= mismatch_next;
                seen <= seen + 1'b1;
            end
        end
    end

    assign pin_match = matched;

    // The stage selects a colour, and stage three is the verdict, so the light is the die's answer and not the
    // host's opinion of the run.
    reg red;
    reg green;
    reg blue;

    always @(*) begin
        case (stage)
            2'd0:    {red, green, blue} = 3'b001;
            2'd1:    {red, green, blue} = 3'b011;
            2'd2:    {red, green, blue} = 3'b110;
            2'd3:    {red, green, blue} = matched ? 3'b010 : 3'b100;
            default: {red, green, blue} = 3'b000;
        endcase
    end

    // A part that sits still reads as a photograph of a part. Every stage but the verdict blinks, and the verdict
    // is steady.
    reg [24:0] heart = 25'd0;

    always @(posedge clk)
        heart <= heart + 1'b1;

    wire beat = heart[24];
    wire hold = stage == 2'd3;

    assign led_red   = red   && (beat || hold);
    assign led_green = green && (beat || hold);
    assign led_blue  = blue  && (beat || hold);

endmodule
