//! SSCCS custom instruction definitions and encodings for RISC-V.
//!
//! Defines observation, collapse, field_update, layout, and adjacency
//! primitives as custom RISC-V instructions using `custom1` and `custom2`
//! opcode spaces, following the RISC-V specification and OpenHW CORE-V XIF.
//!
//! Instruction encoding (custom1 opcode = 0x0B, custom2 opcode = 0x2B):
//! | funct3 | operation     | concept       |
//! |--------|---------------|---------------|
//! | 000    | OBSERVE       | observation   |
//! | 001    | COLLAPSE      | collapse      |
//! | 010    | FIELD_UPDATE  | field         |
//! | 011    | LAYOUT_MAP    | scheme layout |
//! | 100    | ADJACENCY     | adjacency     |
//! | 101-111| (reserved)    |               |

/// Custom opcode for observation primitives (custom1).
pub const OBSERVE_OPCODE: u8 = 0x0B;
/// Alternative custom opcode for extended operations (custom2).
pub const OBSERVE_EXT_OPCODE: u8 = 0x2B;

// ── funct3 codes per SSCCS concept ──
pub const FUNCT3_OBSERVE: u8 = 0b000;
pub const FUNCT3_COLLAPSE: u8 = 0b001;
pub const FUNCT3_FIELD_UPDATE: u8 = 0b010;
pub const FUNCT3_LAYOUT_MAP: u8 = 0b011;
pub const FUNCT3_ADJACENCY: u8 = 0b100;

// ── function codes (instruction subtype, encoded in rs3 or immediate) ──

/// Observation sub-operations.
pub const OP_OBSERVE: u8 = 0x00;
pub const OP_OBSERVE_BATCH: u8 = 0x01;

/// Collapse sub-operations.
pub const OP_COLLAPSE_SUM: u8 = 0x00;
pub const OP_COLLAPSE_MIN: u8 = 0x01;
pub const OP_COLLAPSE_MAX: u8 = 0x02;
pub const OP_COLLAPSE_PRODUCT: u8 = 0x03;
pub const OP_COLLAPSE_COUNT: u8 = 0x04;
pub const OP_COLLAPSE_WEIGHTED_SUM: u8 = 0x05;
pub const OP_COLLAPSE_WEIGHTED_AVG: u8 = 0x06;
pub const OP_COLLAPSE_BATCH: u8 = 0x07;

/// Field update sub-operations.
pub const OP_FIELD_ADD_CONSTRAINT: u8 = 0x00;
pub const OP_FIELD_REMOVE_CONSTRAINT: u8 = 0x01;
pub const OP_FIELD_ADD_TRANSITION: u8 = 0x02;
pub const OP_FIELD_UPDATE_WEIGHT: u8 = 0x03;
pub const OP_FIELD_GET_TRANSITIONS: u8 = 0x04;
pub const OP_FIELD_CLEAR: u8 = 0x05;

/// Layout sub-operations.
pub const OP_LAYOUT_LINEAR_1D: u8 = 0x00;
pub const OP_LAYOUT_LINEAR_ND: u8 = 0x01;
pub const OP_LAYOUT_ROW_MAJOR_2D: u8 = 0x02;
pub const OP_LAYOUT_ROW_MAJOR_3D: u8 = 0x03;
pub const OP_LAYOUT_COL_MAJOR_2D: u8 = 0x04;
pub const OP_LAYOUT_ZORDER_2D: u8 = 0x05;
pub const OP_LAYOUT_BATCH: u8 = 0x06;

/// Adjacency sub-operations.
pub const OP_ADJ_GRID_4: u8 = 0x00;
pub const OP_ADJ_GRID_8: u8 = 0x01;
pub const OP_ADJ_MANHATTAN_1D: u8 = 0x02;
pub const OP_ADJ_GRAPH_EDGES: u8 = 0x03;
pub const OP_ADJ_BATCH: u8 = 0x04;

/// Encodes a custom R-type instruction.
/// Fields: func (rs3), rs2, rs1, funct3, opcode
pub fn encode_custom_rtype(rs3: u8, rs2: u8, rs1: u8, funct3: u8, opcode: u8) -> u32 {
    ((rs3 as u32) << 27)
        | ((rs2 as u32) << 20)
        | ((rs1 as u32) << 15)
        | ((funct3 as u32) << 12)
        | (opcode as u32)
}

/// Decodes a custom instruction, returning (func, rs2, rs1, funct3, opcode).
pub fn decode_custom(inst: u32) -> (u8, u8, u8, u8, u8) {
    let rs3 = ((inst >> 27) & 0x1F) as u8;
    let rs2 = ((inst >> 20) & 0x1F) as u8;
    let rs1 = ((inst >> 15) & 0x1F) as u8;
    let funct3 = ((inst >> 12) & 0x7) as u8;
    let opcode = (inst & 0x7F) as u8;
    (rs3, rs2, rs1, funct3, opcode)
}

// ═══════════════════════════════════════════════════════════════════════
// Software emulation (all platforms)
// ═══════════════════════════════════════════════════════════════════════

// The canonical assembly implementation lives in the raw `asm/*.S` modules
// (RV64, executed under Spike and pinned by golden anchors). This module
// intentionally carries no inline assembly: the Rust side only defines the
// custom instruction encodings above and the host-verifiable software
// emulation below, so RTL conversion has a single assembly substrate to read.

/// Software emulation of OBSERVE.
pub fn observe_emulate(scheme_id: u32, field_id: u32, rule_id: u32) -> u32 {
    let mut hash = scheme_id.wrapping_mul(0x9e3779b9);
    hash ^= field_id.wrapping_mul(0x243f6a88);
    hash ^= rule_id.wrapping_mul(0x85a308d3);
    hash
}

/// Software emulation of COLLAPSE (sum by default).
pub fn collapse_emulate(coords: &[i64]) -> i64 {
    coords.iter().sum()
}

/// Software emulation of field_add_constraint.
pub fn field_add_constraint_emulate(
    field: &mut FieldState,
    constraint_fn: usize,
    constraint_id: u32,
) -> i32 {
    if field.num_constraints >= 8 {
        return -1;
    }
    field.constraint_fns[field.num_constraints as usize] = constraint_fn;
    field.constraint_ids[field.num_constraints as usize] = constraint_id;
    field.num_constraints = field.num_constraints.wrapping_add(1);
    0
}

/// Software emulation of layout_row_major_2d.
pub fn layout_row_major_2d_emulate(x: i64, y: i64, width: i64, elem_size: i64) -> i64 {
    (y * width + x) * elem_size
}

/// Software emulation of adj_grid_4.
pub fn adj_grid_4_emulate(
    x: i64,
    y: i64,
    min_x: i64,
    max_x: i64,
    min_y: i64,
    max_y: i64,
) -> Vec<(i64, i64)> {
    let mut result = Vec::with_capacity(4);
    if x + 1 <= max_x {
        result.push((x + 1, y));
    }
    if x - 1 >= min_x {
        result.push((x - 1, y));
    }
    if y + 1 <= max_y {
        result.push((x, y + 1));
    }
    if y - 1 >= min_y {
        result.push((x, y - 1));
    }
    result
}

/// Minimal field state for software emulation.
#[derive(Debug, Clone)]
pub struct FieldState {
    pub constraint_fns: [usize; 8],
    pub constraint_ids: [u32; 8],
    pub transitions: [(i64, i64, i64); 16],
    pub num_constraints: u32,
    pub num_transitions: u32,
}

impl FieldState {
    pub fn new() -> Self {
        Self {
            constraint_fns: [0; 8],
            constraint_ids: [0; 8],
            transitions: [(0, 0, 0); 16],
            num_constraints: 0,
            num_transitions: 0,
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encode_decode() {
        let inst = encode_custom_rtype(1, 2, 3, FUNCT3_OBSERVE, OBSERVE_OPCODE);
        let (rs3, rs2, rs1, funct3, opcode) = decode_custom(inst);
        assert_eq!(rs3, 1);
        assert_eq!(rs2, 2);
        assert_eq!(rs1, 3);
        assert_eq!(funct3, FUNCT3_OBSERVE);
        assert_eq!(opcode, OBSERVE_OPCODE);
    }

    #[test]
    fn test_observe_emulate() {
        let result = observe_emulate(0x1234, 0x5678, 0x9ABC);
        assert_ne!(result, 0);
    }

    #[test]
    fn test_collapse_emulate() {
        assert_eq!(collapse_emulate(&[2, 4, 6, 8]), 20);
        assert_eq!(collapse_emulate(&[]), 0);
    }

    #[test]
    fn test_field_add_constraint_emulate() {
        let mut field = FieldState::new();
        assert_eq!(field_add_constraint_emulate(&mut field, 0x1000, 1), 0);
        assert_eq!(field.num_constraints, 1);
        assert_eq!(field.constraint_ids[0], 1);
    }

    #[test]
    fn test_layout_row_major_2d_emulate() {
        let offset = layout_row_major_2d_emulate(1, 2, 10, 8);
        assert_eq!(offset, (2 * 10 + 1) * 8);
    }

    #[test]
    fn test_adj_grid_4_emulate() {
        let neighbors = adj_grid_4_emulate(2, 2, 0, 4, 0, 4);
        assert_eq!(neighbors.len(), 4);
        let corner = adj_grid_4_emulate(0, 0, 0, 4, 0, 4);
        assert_eq!(corner.len(), 2);
    }

    #[test]
    fn test_funct3_codes_unique() {
        let codes = [
            FUNCT3_OBSERVE,
            FUNCT3_COLLAPSE,
            FUNCT3_FIELD_UPDATE,
            FUNCT3_LAYOUT_MAP,
            FUNCT3_ADJACENCY,
        ];
        let mut sorted = codes;
        sorted.sort();
        let deduped = {
            let mut v: Vec<u8> = sorted.to_vec();
            v.dedup();
            v
        };
        assert_eq!(deduped.len(), codes.len(), "funct3 codes must be unique");
    }
}
