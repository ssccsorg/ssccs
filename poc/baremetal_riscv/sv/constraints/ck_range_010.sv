// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS CONSTRAINT: ck_range_010 — hardcoded [0,10]                  ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:ck_range_0_10):              ║
// ║    li  t1, 11                                                       ║
// ║    sltu a0, t0, t1   // coord < 11 → 1, else 0                      ║
// ║                                                                    ║
// ║  Synthesis: 1 LUT6 carry-chain comparator, 0 registers              ║
// ╚══════════════════════════════════════════════════════════════════════╝

module ck_range_010 (
    input  wire logic [63:0] coord,
    output wire logic        result
);

    // Unsigned comparison: coord < 11 covers [0,10]
    assign result = (coord < 64'd11);

endmodule
