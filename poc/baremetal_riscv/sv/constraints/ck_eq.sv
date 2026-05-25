// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS CONSTRAINT: ck_eq — equality check                           ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:ck_eq_val):                  ║
// ║    ld   t0, 0(a0)                                                   ║
// ║    xor  t0, t0, a1     // difference                                 ║
// ║    seqz a0, t0         // 1 if equal                                 ║
// ║                                                                    ║
// ║  Synthesis: 64-bit XOR + reduction-NOR, 0 registers                 ║
// ╚══════════════════════════════════════════════════════════════════════╝

module ck_eq #(
    parameter logic [63:0] TARGET = 64'd0
) (
    input  wire logic [63:0] coord,
    output wire logic        result
);

    assign result = (coord == TARGET);

endmodule
