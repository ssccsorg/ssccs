// ╔══════════════════════════════════════════════════════════════════════╗
// ║  SSCCS GOLDEN ANCHORS — extracted from .S files                     ║
// ║                                                                    ║
// ║  These values MUST match the GOLDEN_* anchors in:                   ║
// ║    asm/observe_full.S                                               ║
// ║    asm/collapse.S                                                   ║
// ║    asm/field_update.S                                               ║
// ║    asm/scheme_layout.S                                              ║
// ║    asm/scheme_adjacency.S                                           ║
// ║                                                                    ║
// ║  If a .S file changes, this file MUST be updated to match.          ║
// ║  The testbench asserts against these values.                        ║
// ╚══════════════════════════════════════════════════════════════════════╝

`ifndef SSCCS_GOLDEN_ANCHORS_SVH
`define SSCCS_GOLDEN_ANCHORS_SVH

// ── observe_full.S anchors ──
// GOLDEN_SEGMENTS: 2,3,5,10,12
`define GOLDEN_SEG_0  64'd2
`define GOLDEN_SEG_1  64'd3
`define GOLDEN_SEG_2  64'd5
`define GOLDEN_SEG_3  64'd10
`define GOLDEN_SEG_4  64'd12

// GOLDEN_NARROW: 2,REJECT,REJECT,10,REJECT
// REJECT = i64::MIN = 0x8000000000000000
`define GOLDEN_NARROW_0  64'd2
`define GOLDEN_NARROW_1  64'h8000000000000000
`define GOLDEN_NARROW_2  64'h8000000000000000
`define GOLDEN_NARROW_3  64'd10
`define GOLDEN_NARROW_4  64'h8000000000000000

// GOLDEN_BROAD: 2,3,5,10,12
`define GOLDEN_BROAD_0  64'd2
`define GOLDEN_BROAD_1  64'd3
`define GOLDEN_BROAD_2  64'd5
`define GOLDEN_BROAD_3  64'd10
`define GOLDEN_BROAD_4  64'd12

// GOLDEN_SUM3D_A: 3
// GOLDEN_SUM3D_B: 6
`define GOLDEN_SUM3D_A  64'd3
`define GOLDEN_SUM3D_B  64'd6

// GOLDEN_PARITY_2: 0
// GOLDEN_PARITY_3: 1
`define GOLDEN_PARITY_2  64'd0
`define GOLDEN_PARITY_3  64'd1

// ── collapse.S anchors ──
`define GOLDEN_COLLAPSE_SUM_A  64'd20
`define GOLDEN_COLLAPSE_SUM_B  64'd16
`define GOLDEN_COLLAPSE_MIN_A  64'd2
`define GOLDEN_COLLAPSE_MAX_B  64'd7
`define GOLDEN_COLLAPSE_PROD_A  64'd384
`define GOLDEN_COLLAPSE_COUNT_A  64'd4
`define GOLDEN_COLLAPSE_WEIGHTED_SUM_A  64'd32
`define GOLDEN_COLLAPSE_WEIGHTED_AVG_A  64'd5

// ── field_update.S anchors ──
`define GOLDEN_FIELD_ADD_CONSTRAINT  64'd0
`define GOLDEN_FIELD_REMOVE_CONSTRAINT  64'd0
`define GOLDEN_FIELD_ADD_TRANSITION  64'd0
`define GOLDEN_FIELD_UPDATE_WEIGHT  64'd0

// ── scheme_layout.S anchors ──
`define GOLDEN_LAYOUT_LINEAR_1D  64'd42
`define GOLDEN_LAYOUT_ROW_MAJOR_2D  64'd42
`define GOLDEN_LAYOUT_COL_MAJOR_2D  64'd34
`define GOLDEN_MORTON_2D  64'd9

// ── scheme_adjacency.S anchors ──
`define GOLDEN_ADJ_GRID_4_CENTER  64'd4
`define GOLDEN_ADJ_GRID_4_CORNER  64'd2
`define GOLDEN_ADJ_GRID_8_CENTER  64'd8
`define GOLDEN_ADJ_GRID_8_CORNER  64'd3
`define GOLDEN_ADJ_MANHATTAN_1D_D1  64'd2
`define GOLDEN_ADJ_MANHATTAN_1D_D2  64'd4

// REJECT sentinel value
`define REJECT_SENTINEL  64'h8000000000000000

`endif
