// SPDX-License-Identifier: LicenseRef-SSCCS-Research-Preview
// Copyright (c) 2026 Taeho Lee, SSCCS Initiative.
//
// Research in progress. Read, check, and cite it. See LICENSE at the root of
// this proof of concept before copying it into another work.
//
// SSCCS Projector: Identity
// proj_id(coord) → coord[0]
//
// RISC-V asm equivalent (observe_full.S:proj_id):
//   ld a0, 0(a0)

module proj_identity (
    input  logic [63:0] coord,
    output logic [63:0] result
);

    assign result = coord;

endmodule
