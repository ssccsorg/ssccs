// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (C) 2026 Taeho Lee
//
// This source describes Open Hardware and is licensed under the CERN-OHL-P v2.
// You may redistribute and modify this documentation and make products using
// it under the terms of the CERN-OHL-P v2 (https://cern.ch/cern-ohl). This
// documentation is distributed WITHOUT ANY EXPRESS OR IMPLIED WARRANTY,
// INCLUDING OF MERCHANTABILITY, SATISFACTORY QUALITY AND FITNESS FOR A
// PARTICULAR PURPOSE. Please see the CERN-OHL-P v2 for applicable conditions.
//
// SSCCS Projector: Parity
// proj_parity(coord) → coord[0] & 1
//
// RISC-V asm equivalent (observe_full.S:proj_parity):
//   ld   t0, 0(a0)
//   andi a0, t0, 1

module proj_parity (
    input  logic [63:0] coord,
    output logic [63:0] result
);

    assign result = {63'd0, coord[0]};

endmodule
