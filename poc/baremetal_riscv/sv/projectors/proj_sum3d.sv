// SSCCS Projector: Sum3D
// proj_sum3d(coord) → coord[0] + coord[1] + coord[2]
//
// RISC-V asm equivalent (observe_full.S:proj_sum3d):
//   ld  t0, 0(a0)
//   ld  t1, 8(a0)
//   ld  t2, 16(a0)
//   add t0, t0, t1
//   add a0, t0, t2

module proj_sum3d (
    input  logic [63:0] coord_a,
    input  logic [63:0] coord_b,
    input  logic [63:0] coord_c,
    output logic [63:0] result
);

    assign result = coord_a + coord_b + coord_c;

endmodule
