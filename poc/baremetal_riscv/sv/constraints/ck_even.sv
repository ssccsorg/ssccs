// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS CONSTRAINT: ck_even                                          ║
// ║  SystemVerilog Reference — purely combinational, zero branches      ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:ck_even):                    ║
// ║    ld   t0, 0(a0)    // load i64                                    ║
// ║    andi t0, t0, 1    // mask LSB                                     ║
// ║    xori a0, t0, 1    // 1=even, 0=odd                               ║
// ║                                                                    ║
// ║  Synthesis: 1 LUT6 (3-input XOR of AND result), 0 registers         ║
// ╚══════════════════════════════════════════════════════════════════════╝

module ck_even (
    input  wire logic [63:0] coord,
    output wire logic        result
);

    // coord[0] == 0  →  even  →  result = 1
    // coord[0] == 1  →  odd   →  result = 0
    assign result = ~coord[0];

endmodule
