// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (C) 2026 Taeho Lee
//
// This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
// You may redistribute and modify this documentation and make products using
// it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
// documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
// INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
// PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
//
// Both halves of a substrate on one die: the address map and the field.
//
// The other two images read coordinate tables. This one has none: the address is the sweep, an emitted decoder turns
// it into the coordinate the Scheme holds there, and an emitted observation module decides whether that coordinate is
// admissible. The die counts the admissions and compares the total with the number the host computed from the same
// Scheme and the same program.
//
// The space is a line of sixteen points three apart, so the address is not the coordinate and the decode is
// arithmetic rather than a wire. The program is `even and range [0, 10]`, which admits two of the sixteen. A decoder
// that passed the address through would give six, so the count distinguishes the two.
//
// The count is a single word read from the table the host wrote, and the control is that word plus one, which the die
// must refuse. Nothing here names the Scheme or the program: changing either changes the modules and the count.

`include "_units.svh"

module ssccs_decoded_board #(
    parameter integer COUNT = 0
) (
    input  wire       clk_in,
    input  wire [1:0] stage,
    output wire       pin_match,
    output wire       led_red,
    output wire       led_green,
    output wire       led_blue
);

    wire clk = clk_in;

    localparam integer ADDR_BITS = (COUNT > 1) ? $clog2(COUNT) : 1;

    reg [ADDR_BITS-1:0] addr = 0;

    wire [63:0] coord;
    wire        in_space;

    ssccs_line_decode u_decode (
        .addr(addr),
        .coord0(coord),
        .valid(in_space)
    );

    wire [63:0] result;
    wire        admitted;

    ssccs_generated_narrow u_observe (
        .coord(coord),
        .result(result),
        .valid(admitted)
    );

    // The number the host counted, and one off it for the control.
    reg [63:0] planned [0:0];

`ifdef SIM
    reg [1023:0] count_file;

    initial begin
        if (!$value$plusargs("count=%s", count_file)) count_file = "out/decode_count.hex";
        $readmemh(count_file, planned);
    end
`else
    initial begin
        $readmemh("out/decode_count.hex", planned);
    end
`endif

    // One address per clock. The decoder and the observation are combinational, so the address held this clock is
    // what the next count includes, and the closing edge compares the total of the whole space.
    reg [63:0] admissions = 64'd0;
    reg [ADDR_BITS-1:0] seen = 0;
    reg matched = 1'b0;

    wire [63:0] next_total = admissions + (admitted && in_space ? 64'd1 : 64'd0);

    always @(posedge clk) begin
        if (seen == COUNT - 1) begin
            matched <= (next_total == planned[0]);
            admissions <= 64'd0;
            seen <= {ADDR_BITS{1'b0}};
            addr <= {ADDR_BITS{1'b0}};
        end else begin
            admissions <= next_total;
            seen <= seen + 1'b1;
            addr <= addr + 1'b1;
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

    reg [24:0] heart = 25'd0;

    always @(posedge clk)
        heart <= heart + 1'b1;

    wire beat = heart[24];
    wire hold = stage == 2'd3;

    assign led_red   = red   && (beat || hold);
    assign led_green = green && (beat || hold);
    assign led_blue  = blue  && (beat || hold);

endmodule
