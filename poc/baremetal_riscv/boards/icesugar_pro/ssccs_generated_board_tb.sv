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
// The generated image against a table, so the top has a gate that does not need the board.
//
// The three tables come from `+coord=`, `+narrow=` and `+broad=` and the expected verdict from `+expect=`, which is
// the same contract as the anchor image's testbench. There is no `+inquiry=`: this design has no table of kinds.
//
//   +coord=out/pass/anchor_coord.hex +narrow=out/pass/anchor_narrow.hex +broad=out/pass/anchor_broad.hex +expect=1
//   +coord=out/swap/anchor_coord.hex +narrow=out/swap/anchor_narrow.hex +broad=out/swap/anchor_broad.hex +expect=0

module ssccs_generated_board_tb #(
    parameter integer COUNT = 5
) ();

    reg clk = 1'b0;
    reg [1:0] stage = 2'd3;

    wire pin_match;
    wire led_red;
    wire led_green;
    wire led_blue;

    ssccs_generated_board #(
        .COUNT(COUNT)
    ) dut (
        .clk_in(clk),
        .stage(stage),
        .pin_match(pin_match),
        .led_red(led_red),
        .led_green(led_green),
        .led_blue(led_blue)
    );

    always #5 clk = ~clk;

    integer want = 1;
    integer guard;

    initial begin
        if (!$value$plusargs("expect=%d", want)) want = 1;

        // Four sweeps: the first may still be filling when it starts, and the comparison is one line per clock.
        guard = 4 * (COUNT + 16);
        repeat (guard) @(posedge clk);

        if (pin_match !== (want != 0)) begin
            $display("FAIL: pin_match=%0d, expected %0d after %0d clocks over %0d anchors",
                     pin_match, want, guard, COUNT);
            $fatal(1);
        end

        if (led_green !== pin_match || led_red !== !pin_match || led_blue !== 1'b0) begin
            $display("FAIL: stage 3 lit red=%0d green=%0d blue=%0d for pin_match=%0d",
                     led_red, led_green, led_blue, pin_match);
            $fatal(1);
        end

        $display("PASS: pin_match=%0d over %0d anchors in %0d clocks", pin_match, COUNT, guard);
        $finish;
    end

endmodule
