// SPDX-License-Identifier: LicenseRef-Proprietary
// Copyright (C) 2026 Taeho Lee, SSCCS Initiative. All rights reserved.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// The emitted modules against the anchors.
//
// Both modules below came from ssccs-hardware-mapping, not from this tree: `make generate` runs the host emitter
// and writes them into generated/. That makes the anchors a check on the emitter as well as on the die, which is
// what a second consumer of the same semantics is for.
//
// The pair share their constraints and differ only in the join, so the two tables below say what the join does:
// the narrow module admits 2 and 10, the broad module admits every coordinate the anchors carry.

`include "_golden_anchors.svh"

module generated_observation_tb;

    reg [63:0] coord;

    wire [63:0] narrow_result;
    wire [63:0] broad_result;
    wire        narrow_valid;
    wire        broad_valid;

    ssccs_generated_narrow u_narrow (
        .coord(coord),
        .result(narrow_result),
        .valid(narrow_valid)
    );

    ssccs_generated_broad u_broad (
        .coord(coord),
        .result(broad_result),
        .valid(broad_valid)
    );

    // The anchors, as the two modules' inputs and expectations.
    reg [63:0] seg [0:4];
    reg [63:0] narrow [0:4];
    reg [63:0] broad [0:4];

    integer i;
    integer errors = 0;

    initial begin
        seg[0] = `GOLDEN_SEG_0;
        seg[1] = `GOLDEN_SEG_1;
        seg[2] = `GOLDEN_SEG_2;
        seg[3] = `GOLDEN_SEG_3;
        seg[4] = `GOLDEN_SEG_4;

        narrow[0] = `GOLDEN_NARROW_0;
        narrow[1] = `GOLDEN_NARROW_1;
        narrow[2] = `GOLDEN_NARROW_2;
        narrow[3] = `GOLDEN_NARROW_3;
        narrow[4] = `GOLDEN_NARROW_4;

        broad[0] = `GOLDEN_BROAD_0;
        broad[1] = `GOLDEN_BROAD_1;
        broad[2] = `GOLDEN_BROAD_2;
        broad[3] = `GOLDEN_BROAD_3;
        broad[4] = `GOLDEN_BROAD_4;

        // The modules are combinational, so one time unit past the input assignment settles them.
        for (i = 0; i < 5; i = i + 1) begin
            coord = seg[i];
            #1;

            if (narrow[i] == `REJECT_SENTINEL) begin
                if (narrow_valid) begin
                    errors = errors + 1;
                    $display("narrow coord %0d: expected a rejection, got 0x%016h", $signed(seg[i]), narrow_result);
                end
            end else if (!narrow_valid || narrow_result !== narrow[i]) begin
                errors = errors + 1;
                $display("narrow coord %0d: expected 0x%016h, got 0x%016h (valid %0d)",
                         $signed(seg[i]), narrow[i], narrow_result, narrow_valid);
            end

            if (broad[i] == `REJECT_SENTINEL) begin
                if (broad_valid) begin
                    errors = errors + 1;
                    $display("broad coord %0d: expected a rejection, got 0x%016h", $signed(seg[i]), broad_result);
                end
            end else if (!broad_valid || broad_result !== broad[i]) begin
                errors = errors + 1;
                $display("broad coord %0d: expected 0x%016h, got 0x%016h (valid %0d)",
                         $signed(seg[i]), broad[i], broad_result, broad_valid);
            end
        end

        if (errors == 0)
            $display("All Golden Anchors Verified (emitted modules)");
        else
            $fatal(1, "%0d anchors disagree with the emitted modules", errors);
    end

endmodule
