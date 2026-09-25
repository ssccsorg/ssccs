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
