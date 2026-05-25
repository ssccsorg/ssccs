// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS CONSTRAINT: ck_gt — greater-than check                       ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:ck_gt):                      ║
// ║    ld  t0, 0(a0)                                                    ║
// ║    slt a0, a1, t0     // 1 if target < coord                         ║
// ║                                                                    ║
// ║  Synthesis: 1 comparator, 0 registers                               ║
// ╚══════════════════════════════════════════════════════════════════════╝

module ck_gt #(
    parameter logic [63:0] THRESHOLD = 64'd0
) (
    input  wire logic [63:0] coord,
    output wire logic        result
);

    assign result = (coord > THRESHOLD);

endmodule
