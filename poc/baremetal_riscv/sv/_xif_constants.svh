// SSCCS XIF Coprocessor Constants
//
// Shared opcode, funct3, and sub-operation definitions for:
//   ssccs_xif_coprocessor.sv (DUT)
//   xif_integration_tb.sv      (testbench)
//
// Single source of truth for the custom instruction encoding.

`ifndef SSCCS_XIF_CONSTANTS_SVH
`define SSCCS_XIF_CONSTANTS_SVH

// Opcode constants
`define OPCODE_CUSTOM1  7'b0001011
`define OPCODE_CUSTOM2  7'b0101011

// funct3 constants for custom1
`define FUNCT3_OBSERVE    3'b000
`define FUNCT3_CONSTRAINT 3'b001
`define FUNCT3_COMPOSE    3'b010

// funct3 constants for custom2
`define FUNCT3_PROJECT    3'b000
`define FUNCT3_COLLAPSE   3'b001

// Sub-operation IDs (passed via rs2[2:0] for CONSTRAINT, COMPOSE, PROJECT)
//
// Operand mapping:
//   rs1 = coordinate
//   rs2[2:0] = sub-op ID, rs2[63:3] = parameter
//   rs3 = extra operand (MIN_VAL for ck_range, coord_c for proj_sum3d)
`define OP_CK_EVEN       3'd0
`define OP_CK_RANGE_010  3'd1
`define OP_CK_RANGE      3'd2
`define OP_CK_EQ         3'd3
`define OP_CK_GT         3'd4
`define OP_COMPOSE_AND   3'd0
`define OP_COMPOSE_OR    3'd1
`define OP_PROJ_ID       3'd0
`define OP_PROJ_SUM2D    3'd1
`define OP_PROJ_SUM3D    3'd2
`define OP_PROJ_PARITY   3'd3
`define OP_PROJ_NEGATE   3'd4

`endif
