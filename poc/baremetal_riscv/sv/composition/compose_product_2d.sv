// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS COMPOSITION: Product (×) for 2×1D                            ║
// ║  C((x,y)) = C₁(x) ∧ C₂(y)                                           ║
// ║                                                                    ║
// ║  RISC-V asm equivalent (observe_full.S:compose_product_2d):         ║
// ║    left  = coord[0]; call fa(left)  → C₁                            ║
// ║    right = coord[1]; call fb(right) → C₂                            ║
// ║    and a0, t0, t0    // C₁ ∧ C₂                                     ║
// ║                                                                    ║
// ║  Synthesis: 2 constraint modules in parallel + AND gate             ║
// ╚══════════════════════════════════════════════════════════════════════╝

module compose_product_2d (
    input  wire logic [63:0] coord_left,
    input  wire logic [63:0] coord_right,
    input  wire logic        c1_result,
    input  wire logic        c2_result,
    output wire logic        result
);

    assign result = c1_result && c2_result;

endmodule
