// SSCCS Observation Engine — RISC-V XIF Coprocessor Top-Level
//
// Wraps constraint, composition, and projector modules behind a
// standard RISC-V XIF (eXtension Interface) coprocessor port.
//
// Custom instruction encoding (matches observe_full.S):
//
//   custom1 (opcode 0001011):
//     funct3=000: OBSERVE    — constraint check → projection
//     funct3=001: CONSTRAINT — single constraint evaluation
//     funct3=010: COMPOSE    — field composition (intersect/union)
//
//   custom2 (opcode 0101011):
//     funct3=000: PROJECT    — projector evaluation
//     funct3=001: COLLAPSE   — reduction (future)
//
// XIF signal protocol:
//   Core issues: xif_issue_valid, xif_issue_req.{opcode,funct3,...}
//   Coprocessor:  xif_issue_ready, xif_result_valid, xif_result.data
//
// Reference: OpenHW CORE-V XIF Specification
//   https://github.com/openhwgroup/core-v-xif

`include "_golden_anchors.svh"
`include "_xif_constants.svh"

module ssccs_xif_coprocessor (
    input  logic        clk,
    input  logic        rst_n,

    // XIF Issue Interface
    input  logic        xif_issue_valid,
    output logic        xif_issue_ready,
    input  logic [31:0] xif_issue_req_instr,   // full instruction word
    input  logic [63:0] xif_issue_req_rs1,     // operand A
    input  logic [63:0] xif_issue_req_rs2,     // operand B (also carries sub-op ID)
    input  logic [63:0] xif_issue_req_rs3,     // operand C (for 3-operand ops)

    // XIF Result Interface
    output logic        xif_result_valid,
    input  logic        xif_result_ready,
    output logic [63:0] xif_result_data,
    output logic [4:0]  xif_result_rd,         // destination register
    output logic        xif_result_exc          // exception flag
);

    // Instruction decode
    wire [6:0]  opcode = xif_issue_req_instr[6:0];
    wire [2:0]  funct3 = xif_issue_req_instr[14:12];
    wire [4:0]  rd     = xif_issue_req_instr[11:7];

    // Sub-operation selector (from rs2 LSBs for routing)
    wire [2:0]  sub_op = xif_issue_req_rs2[2:0];

    // Operands
    wire [63:0] coord  = xif_issue_req_rs1;
    wire [63:0] param  = xif_issue_req_rs2;
    wire [63:0] extra  = xif_issue_req_rs3;

    // Combinational results from each unit
    logic ck_even_r, ck_range010_r, ck_range_r, ck_eq_r, ck_gt_r;
    logic compose_and_r, compose_or_r;
    logic [63:0] proj_id_r, proj_parity_r, proj_negate_r;
    logic [63:0] proj_sum2d_r, proj_sum3d_r;

    // Instantiate all functional units (combinational)

    ck_even u_ck_even (.coord(coord), .result(ck_even_r));
    ck_range_010 u_ck_range010 (.coord(coord), .result(ck_range010_r));

    // Range check: MIN_VAL from rs3 (defaults to 0), MAX_VAL from rs2
    ck_range #(
        .MIN_VAL(extra),
        .MAX_VAL(param)
    ) u_ck_range (.coord(coord), .result(ck_range_r));

    ck_eq #(.TARGET(param))     u_ck_eq (.coord(coord), .result(ck_eq_r));
    ck_gt #(.THRESHOLD(param))  u_ck_gt (.coord(coord), .result(ck_gt_r));

    // Composition: uses two constraint results from external registers
    // (rs1 = C₁ result, rs2 = C₂ result)
    assign compose_and_r = xif_issue_req_rs1[0] && xif_issue_req_rs2[0];
    assign compose_or_r  = xif_issue_req_rs1[0] || xif_issue_req_rs2[0];

    // Projectors
    proj_identity u_proj_id    (.coord(coord), .result(proj_id_r));
    proj_sum2d    u_proj_sum2d (.coord_a(coord), .coord_b(param), .result(proj_sum2d_r));
    proj_sum3d    u_proj_sum3d (.coord_a(coord), .coord_b(param), .coord_c(extra),
                                .result(proj_sum3d_r));
    proj_parity   u_proj_par  (.coord(coord), .result(proj_parity_r));
    proj_negate   u_proj_neg  (.coord(coord), .result(proj_negate_r));

    // Operation dispatch (combinational)
    logic        is_custom1, is_custom2;
    logic [63:0] raw_result;
    logic        result_exc;

    assign is_custom1 = (opcode == `OPCODE_CUSTOM1);
    assign is_custom2 = (opcode == `OPCODE_CUSTOM2);

    always_comb begin
        raw_result = 64'd0;
        result_exc = 1'b0;

        if (is_custom1) begin
            case (funct3)
                `FUNCT3_CONSTRAINT: begin
                    case (sub_op)
                        `OP_CK_EVEN:      raw_result = {63'd0, ck_even_r};
                        `OP_CK_RANGE_010: raw_result = {63'd0, ck_range010_r};
                        `OP_CK_RANGE:     raw_result = {63'd0, ck_range_r};
                        `OP_CK_EQ:        raw_result = {63'd0, ck_eq_r};
                        `OP_CK_GT:        raw_result = {63'd0, ck_gt_r};
                        default:          result_exc = 1'b1;
                    endcase
                end

                `FUNCT3_COMPOSE: begin
                    case (sub_op)
                        `OP_COMPOSE_AND: raw_result = {63'd0, compose_and_r};
                        `OP_COMPOSE_OR:  raw_result = {63'd0, compose_or_r};
                        default:         result_exc = 1'b1;
                    endcase
                end

                default: result_exc = 1'b1;
            endcase

        end else if (is_custom2) begin
            case (funct3)
                `FUNCT3_PROJECT: begin
                    case (sub_op)
                        `OP_PROJ_ID:     raw_result = proj_id_r;
                        `OP_PROJ_SUM2D:  raw_result = proj_sum2d_r;
                        `OP_PROJ_SUM3D:  raw_result = proj_sum3d_r;
                        `OP_PROJ_PARITY: raw_result = proj_parity_r;
                        `OP_PROJ_NEGATE: raw_result = proj_negate_r;
                        default:         result_exc = 1'b1;
                    endcase
                end

                default: result_exc = 1'b1;
            endcase

        end else begin
            // Not our opcode — would not be issued in a real system
            result_exc = 1'b1;
        end
    end

    // XIF protocol state machine
    typedef enum logic [1:0] {
        XIF_IDLE,
        XIF_ACCEPT,
        XIF_RESPOND
    } xif_state_t;

    xif_state_t state, next_state;

    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= XIF_IDLE;
        else
            state <= next_state;
    end

    always_comb begin
        next_state     = state;
        xif_issue_ready = 1'b0;
        xif_result_valid = 1'b0;

        case (state)
            XIF_IDLE: begin
                xif_issue_ready = 1'b1;
                if (xif_issue_valid && (is_custom1 || is_custom2))
                    next_state = XIF_ACCEPT;
            end

            XIF_ACCEPT: begin
                // Result available immediately (combinational)
                xif_result_valid = 1'b1;
                if (xif_result_ready)
                    next_state = XIF_RESPOND;
            end

            XIF_RESPOND: begin
                // Handshake complete
                next_state = XIF_IDLE;
            end
        endcase
    end

    // Result register
    always_ff @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            xif_result_data <= 64'd0;
            xif_result_rd   <= 5'd0;
            xif_result_exc  <= 1'b0;
        end else if (state == XIF_IDLE && xif_issue_valid) begin
            xif_result_data <= raw_result;
            xif_result_rd   <= rd;
            xif_result_exc  <= result_exc;
        end
    end

`ifdef FORMAL
    // SVA assertions
    // Single-cycle: result valid in the cycle after issue
    property issue_to_result;
        @(posedge clk) (xif_issue_valid && xif_issue_ready)
            |=> xif_result_valid;
    endproperty
    assert property (issue_to_result);

    // Combinational determinism: same (opcode, funct3, rs1, rs2, rs3) → same result
    property deterministic;
        @(posedge clk) disable iff (!rst_n)
        (xif_issue_valid && $stable(xif_issue_req_instr) &&
         $stable(xif_issue_req_rs1) && $stable(xif_issue_req_rs2) &&
         $stable(xif_issue_req_rs3))
            |=> $stable(raw_result);
    endproperty
    assert property (deterministic);
`endif

endmodule
