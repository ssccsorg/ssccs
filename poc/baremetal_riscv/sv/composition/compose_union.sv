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
// SSCCS Composition: Union (∪)
// C = C₁ ∨ C₂
//
// RISC-V asm equivalent (observe_full.S:compose_or_fast):
//   call fa(coord) → C₁
//   call fb(coord) → C₂
//   or  a0, t0, t1    // C₁ ∨ C₂
//
// Synthesis: purely combinational. Each constraint module is
// instantiated in parallel; their outputs are ORed.

module compose_union #(
    parameter int NUM_CONSTRAINTS = 2
) (
    input  logic [NUM_CONSTRAINTS-1:0] constraint_results,
    output logic                    result
);

    assign result = |constraint_results;

endmodule
