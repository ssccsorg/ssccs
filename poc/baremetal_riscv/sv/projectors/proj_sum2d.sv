// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS PROJECTOR: Sum2D                                            ║
// ║  proj_sum2d(coord) → coord[0] + coord[1]                            ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:proj_sum2d):                 ║
// ║    ld  t0, 0(a0)                                                    ║
// ║    ld  t1, 8(a0)                                                    ║
// ║    add a0, t0, t1                                                   ║
// ╚══════════════════════════════════════════════════════════════════════╝

module proj_sum2d (
    input  wire logic [63:0] coord_a,
    input  wire logic [63:0] coord_b,
    output wire logic [63:0] result
);

    assign result = coord_a + coord_b;

endmodule
