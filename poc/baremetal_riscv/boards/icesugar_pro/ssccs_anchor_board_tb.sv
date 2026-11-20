// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// The board image against a table, so the top has a gate that does not need the board.
//
// The three tables come from `+coord=`, `+narrow=` and `+broad=` and the expected verdict from `+expect=`, so one
// build checks the anchors and the table with two expectations exchanged, which is the negative control.
//
//   +coord=out/pass/anchor_coord.hex +narrow=out/pass/anchor_narrow.hex +broad=out/pass/anchor_broad.hex +expect=1
//   +coord=out/swap/anchor_coord.hex +narrow=out/swap/anchor_narrow.hex +broad=out/swap/anchor_broad.hex +expect=0

module ssccs_anchor_board_tb #(
    parameter integer COUNT = 5
) ();

    reg clk = 1'b0;
    reg [1:0] stage = 2'd3;

    wire pin_match;
    wire led_red;
    wire led_green;
    wire led_blue;

    ssccs_anchor_board #(
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

        // Stage three is steady and carries the verdict, so the colour is the pin.
        if (led_green !== pin_match || led_red !== !pin_match || led_blue !== 1'b0) begin
            $display("FAIL: stage 3 lit red=%0d green=%0d blue=%0d for pin_match=%0d",
                     led_red, led_green, led_blue, pin_match);
            $fatal(1);
        end

        $display("PASS: pin_match=%0d over %0d anchors in %0d clocks", pin_match, COUNT, guard);
        $finish;
    end

endmodule
