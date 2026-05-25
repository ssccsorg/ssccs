// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS OBSERVATION ENGINE — Core Pipeline                           ║
// ║                                                                    ║
// ║  Connects constraint evaluation and projection into the single      ║
// ║  SSCCS observation event: Ω(F, s, π) → Projection                  ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:observe):                    ║
// ║    call field_fn(coord) → C                                         ║
// ║    beqz C → REJECT                                                  ║
// ║    call proj_fn(coord) → result                                     ║
// ║                                                                    ║
// ║  Hot path: 1 comparison + 1 projection, 0 cycles latency            ║
// ║  (purely combinational when constraint and projector are both       ║
// ║   combinational).                                                   ║
// ╚══════════════════════════════════════════════════════════════════════╝

`include "../_golden_anchors.svh"

module observe (
    input  wire logic [63:0] coord,
    input  wire logic        constraint_result,
    input  wire logic [63:0] projection,
    output wire logic [63:0] result,
    output wire logic        valid
);

    assign valid  = constraint_result;
    assign result = constraint_result ? projection : `REJECT_SENTINEL;

endmodule
