// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS CONSTRAINT: ck_range — parameterized [min, max]              ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:ck_range):                   ║
// ║    slt  t1, t0, a1     // coord < min ?                              ║
// ║    slt  t2, a2, t0     // max < coord ?                              ║
// ║    or   t0, t1, t2     // out of range ?                             ║
// ║    xori a0, t0, 1      // invert: 1 = in range                       ║
// ║                                                                    ║
// ║  Synthesis: 2 comparators + OR + NOT, 0 registers                   ║
// ╚══════════════════════════════════════════════════════════════════════╝

module ck_range #(
    parameter logic [63:0] MIN_VAL = 64'd0,
    parameter logic [63:0] MAX_VAL = 64'd10
) (
    input  wire logic [63:0] coord,
    output wire logic        result
);

    assign result = (coord >= MIN_VAL) && (coord <= MAX_VAL);

endmodule
