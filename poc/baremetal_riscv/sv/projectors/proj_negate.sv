// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Owned by the SSCCS Initiative. See LICENSE at the root of this proof of
// concept: a copy carries this notice and the revision it was taken from.
//
// SSCCS Projector: Negate
// proj_negate(coord) → -coord[0]
//
// RISC-V asm equivalent (observe_full.S:proj_negate):
//   ld  t0, 0(a0)
//   neg a0, t0

module proj_negate (
    input  logic [63:0] coord,
    output logic [63:0] result
);

    assign result = -coord;

endmodule
