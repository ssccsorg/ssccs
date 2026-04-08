//! SSCCS custom instruction definitions and encodings for RISC‑V.
//!
//! This module defines the observation primitives as custom RISC‑V instructions
//! using the `custom1` and `custom2` opcode spaces, following the RISC‑V
//! specification and OpenHW CORE‑V XIF interface.

/// Custom opcode for observation primitives (custom1).
pub const OBSERVE_OPCODE: u8 = 0x0B; // custom1
/// Alternative custom opcode for extended observation (custom2).
pub const OBSERVE_EXT_OPCODE: u8 = 0x2B; // custom2

/// Function code for the basic OBSERVE instruction.
pub const FUNCT3_OBSERVE: u8 = 0b000;
/// Function code for COLLAPSE (multi‑segment observation).
pub const FUNCT3_COLLAPSE: u8 = 0b001;
/// Function code for FIELD_UPDATE (update field constraints).
pub const FUNCT3_FIELD_UPDATE: u8 = 0b010;

/// Encodes a custom R‑type instruction.
/// Fields: rs3, rs2, rs1, funct3, opcode
/// Note: The immediate field is zero for R‑type.
pub fn encode_custom_rtype(rs3: u8, rs2: u8, rs1: u8, funct3: u8, opcode: u8) -> u32 {
    ((rs3 as u32) << 27)
        | ((rs2 as u32) << 20)
        | ((rs1 as u32) << 15)
        | ((funct3 as u32) << 12)
        | (opcode as u32)
}

/// Decodes a custom instruction, returning (rs3, rs2, rs1, funct3, opcode).
pub fn decode_custom(inst: u32) -> (u8, u8, u8, u8, u8) {
    let rs3 = ((inst >> 27) & 0x1F) as u8;
    let rs2 = ((inst >> 20) & 0x1F) as u8;
    let rs1 = ((inst >> 15) & 0x1F) as u8;
    let funct3 = ((inst >> 12) & 0x7) as u8;
    let opcode = (inst & 0x7F) as u8;
    (rs3, rs2, rs1, funct3, opcode)
}

/// Inline assembly for the OBSERVE custom instruction.
/// # Safety
/// This function is unsafe because it executes a custom instruction that may
/// not be implemented in the current hardware.
#[cfg(target_arch = "riscv32")]
pub unsafe fn observe(scheme_id: u32, field_id: u32, rule_id: u32) -> u32 {
    let result: u32;
    asm!(
        "custom1 {res}, {s}, {f}, {r}, 0",
        s = in(reg) scheme_id,
        f = in(reg) field_id,
        r = in(reg) rule_id,
        res = out(reg) result,
        options(nostack, preserves_flags)
    );
    result
}

/// Inline assembly for the COLLAPSE custom instruction (custom2).
/// Collapses multiple Segments according to a Scheme.
///
/// # Safety
/// This function is unsafe because it executes a custom instruction that may
/// not be implemented in the current hardware, and its side‑effects are unknown.
#[cfg(target_arch = "riscv32")]
pub unsafe fn collapse(scheme_id: u32, segment_mask: u32, field_id: u32) -> u32 {
    let result: u32;
    asm!(
        "custom2 {res}, {s}, {m}, {f}, 1",
        s = in(reg) scheme_id,
        m = in(reg) segment_mask,
        f = in(reg) field_id,
        res = out(reg) result,
        options(nostack, preserves_flags)
    );
    result
}

/// Software emulation of OBSERVE for environments without custom instruction support.
pub fn observe_emulate(scheme_id: u32, field_id: u32, rule_id: u32) -> u32 {
    // Placeholder: In a full implementation, this would call the SSCCS runtime.
    // For now, return a deterministic hash of the inputs.
    let mut hash = scheme_id.wrapping_mul(0x9e3779b9);
    hash ^= field_id.wrapping_mul(0x243f6a88);
    hash ^= rule_id.wrapping_mul(0x85a308d3);
    hash
}

/// Software emulation of COLLAPSE.
pub fn collapse_emulate(scheme_id: u32, segment_mask: u32, field_id: u32) -> u32 {
    // Placeholder: combine inputs.
    scheme_id.wrapping_add(segment_mask).wrapping_sub(field_id)
}

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
        // Ensure the function returns something (no panic).
        assert_ne!(result, 0);
    }
}
