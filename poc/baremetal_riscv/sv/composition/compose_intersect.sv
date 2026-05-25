// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS COMPOSITION: Intersection (∩)                                ║
// ║  C = C₁ ∧ C₂                                                        ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:compose_and_fast):           ║
// ║    call fa(coord) → C₁                                              ║
// ║    call fb(coord) → C₂                                              ║
// ║    and a0, t0, t1    // C₁ ∧ C₂                                     ║
// ║                                                                    ║
// ║  Synthesis: purely combinational. Each constraint module is         ║
// ║  instantiated in parallel; their outputs are ANDed.                 ║
// ╚══════════════════════════════════════════════════════════════════════╝

module compose_intersect #(
    parameter int NUM_CONSTRAINTS = 2
) (
    input  wire logic [63:0]             coord,
    input  wire logic [NUM_CONSTRAINTS-1:0] constraint_results,
    output wire logic                    result
);

    assign result = &constraint_results;

endmodule
