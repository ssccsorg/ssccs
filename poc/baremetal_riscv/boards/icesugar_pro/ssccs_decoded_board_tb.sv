// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// The decoded image against the host's count, and against a count one off it.
//
//   +count=out/decode_count.hex      +expect=1
//   +count=out/decode_count_off.hex  +expect=0

module ssccs_decoded_board_tb #(
    parameter integer COUNT = 16
) ();

    reg clk = 1'b0;
    reg [1:0] stage = 2'd3;

    wire pin_match;
    wire led_red;
    wire led_green;
    wire led_blue;

    ssccs_decoded_board #(
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

        // Four sweeps of the space: a pass closes when the last address has been counted.
        guard = 4 * (COUNT + 4);
        repeat (guard) @(posedge clk);

        if (pin_match !== (want != 0)) begin
            $display("FAIL: pin_match=%0d, expected %0d after %0d clocks over %0d addresses",
                     pin_match, want, guard, COUNT);
            $fatal(1);
        end

        if (led_green !== pin_match || led_red !== !pin_match || led_blue !== 1'b0) begin
            $display("FAIL: stage 3 lit red=%0d green=%0d blue=%0d for pin_match=%0d",
                     led_red, led_green, led_blue, pin_match);
            $fatal(1);
        end

        $display("PASS: pin_match=%0d over %0d addresses in %0d clocks", pin_match, COUNT, guard);
        $finish;
    end

endmodule
