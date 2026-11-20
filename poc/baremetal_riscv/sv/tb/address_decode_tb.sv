// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// The emitted decoder against the Scheme's own addresses.
//
// The module and the tables both come from the host: `make generate` writes the module from the Scheme's extents and
// the tables from the Scheme's segments. The module computes with division and modulo, the tables are a lookup, so an
// address that lands on the wrong coordinate in one of them is a disagreement between two derivations of one space.
//
// A two-axis space of twelve addresses is what the demo writes, which is why the ports are fixed here. The
// emitter's own tests cover one axis, two axes and three.

module address_decode_tb #(
    parameter integer TOTAL = 12,
    parameter integer WIDTH = 4
) ();

    reg [WIDTH-1:0] addr = 0;

    wire [63:0] coord0;
    wire [63:0] coord1;
    wire        valid;

    ssccs_address_decode dut (
        .addr(addr),
        .coord0(coord0),
        .coord1(coord1),
        .valid(valid)
    );

    reg [63:0] table0 [0:TOTAL-1];
    reg [63:0] table1 [0:TOTAL-1];

    reg [1023:0] file0;
    reg [1023:0] file1;

    integer i;
    integer errors = 0;

    initial begin
        if (!$value$plusargs("coord0=%s", file0)) file0 = "address_coord0.hex";
        if (!$value$plusargs("coord1=%s", file1)) file1 = "address_coord1.hex";
        $readmemh(file0, table0);
        $readmemh(file1, table1);

        for (i = 0; i < TOTAL; i = i + 1) begin
            addr = i[WIDTH-1:0];
            #1;

            if (!valid) begin
                errors = errors + 1;
                $display("address %0d: valid is low inside the space", i);
            end

            if (coord0 !== table0[i] || coord1 !== table1[i]) begin
                errors = errors + 1;
                $display("address %0d: decoded (%0d, %0d), the Scheme holds (%0d, %0d)",
                         i, $signed(coord0), $signed(coord1), $signed(table0[i]), $signed(table1[i]));
            end
        end

        // One address past the space names a point the Scheme does not have, and the module must say so rather than
        // compute something plausible.
        addr = TOTAL[WIDTH-1:0];
        #1;
        if (valid) begin
            errors = errors + 1;
            $display("address %0d: valid is high past the %0d the Scheme holds", addr, TOTAL);
        end

        if (errors == 0)
            $display("All Addresses Verified (emitted decode)");
        else
            $fatal(1, "%0d addresses disagree with the Scheme", errors);
    end

endmodule
