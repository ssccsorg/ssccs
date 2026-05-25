// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS PROJECTOR: Parity                                            ║
// ║  proj_parity(coord) → coord[0] & 1                                  ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:proj_parity):                ║
// ║    ld   t0, 0(a0)                                                   ║
// ║    andi a0, t0, 1                                                   ║
// ╚══════════════════════════════════════════════════════════════════════╝

module proj_parity (
    input  logic [63:0] coord,
    output logic [63:0] result
);

    assign result = {63'd0, coord[0]};

endmodule
