// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview-1.0
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// SSCCS Projector: Sum2D
// proj_sum2d(coord) → coord[0] + coord[1]
//
// RISC-V asm equivalent (observe_full.S:proj_sum2d):
//   ld  t0, 0(a0)
//   ld  t1, 8(a0)
//   add a0, t0, t1

module proj_sum2d (
    input  logic [63:0] coord_a,
    input  logic [63:0] coord_b,
    output logic [63:0] result
);

    assign result = coord_a + coord_b;

endmodule
