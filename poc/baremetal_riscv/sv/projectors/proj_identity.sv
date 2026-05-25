// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS PROJECTOR: Identity                                          ║
// ║  proj_id(coord) → coord[0]                                          ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:proj_id):                    ║
// ║    ld a0, 0(a0)                                                     ║
// ╚══════════════════════════════════════════════════════════════════════╝

module proj_identity (
    input  wire logic [63:0] coord,
    output wire logic [63:0] result
);

    assign result = coord;

endmodule
