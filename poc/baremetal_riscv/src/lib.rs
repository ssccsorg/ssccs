//! SSCCS hardware integration library.
//! Provides primitives for observing SSCCS Schemas via custom RISC‑V instructions
//! and interfaces with the OpenHW CORE‑V XIF coprocessor.

#![cfg_attr(not(test), no_std)]

#[cfg(not(test))]
use panic_halt as _;

pub mod instructions;

/// Emulation of a custom RISC‑V instruction `OBSERVE`.
/// In real hardware this would be implemented as a XIF coprocessor.
/// For now, we provide a software fallback that mimics the observation.
///
/// # Safety
/// This function is safe because it does nothing and always returns a placeholder value.
/// In a real implementation, this would be unsafe due to hardware side‑effects.
pub unsafe fn observe_custom(_scheme_id: u32, _field_id: u32, _rule_id: u32) -> u32 {
    // Placeholder: In hardware, this would be a `custom1` instruction.
    // For software emulation, we call the SSCCS observation runtime.
    // TODO: Integrate with actual SSCCS Scheme and Field.
    0xDEADBEEF
}

/// Inline assembly wrapper for the `OBSERVE` custom instruction.
/// Assumes opcode `custom1` with rs1=scheme_id, rs2=field_id, rs3=rule_id.
///
/// # Safety
/// This function is unsafe because it executes a custom instruction that may
/// not be implemented in the current hardware, and its side‑effects are unknown.
#[cfg(target_arch = "riscv32")]
pub unsafe fn observe_asm(scheme_id: u32, field_id: u32, rule_id: u32) -> u32 {
    let result: u32;
    core::arch::asm!(
        "custom1 {res}, {s}, {f}, {r}",
        s = in(reg) scheme_id,
        f = in(reg) field_id,
        r = in(reg) rule_id,
        res = out(reg) result,
        options(nostack, preserves_flags)
    );
    result
}

/// Hardware profile for OpenHW CORE‑V XIF.
pub struct CoreVXifProfile;

impl CoreVXifProfile {
    /// Maximum number of source registers supported by XIF.
    pub const X_NUM_RS: usize = 3;

    /// Issue an observation via XIF interface.
    /// This is a stub for future hardware implementation.
    pub fn issue_observation(&self, scheme_id: u32, field_id: u32, rule_id: u32) -> u32 {
        // Placeholder: In real hardware, this would trigger XIF signals.
        // For now, delegate to software emulation.
        unsafe { observe_custom(scheme_id, field_id, rule_id) }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_observe_custom() {
        // Just ensure the function doesn't crash.
        let _ = unsafe { observe_custom(0, 0, 0) };
    }

    #[test]
    fn test_instructions_module() {
        // Ensure the instructions module is accessible.
        let _ = instructions::encode_custom_rtype(0, 0, 0, 0, 0);
    }

    #[test]
    fn test_observe_emulate() {
        let result = instructions::observe_emulate(0x1234, 0x5678, 0x9ABC);
        let result2 = instructions::observe_emulate(0x1234, 0x5678, 0x9ABC);
        assert_eq!(result, result2);
    }

    #[test]
    fn test_xif_profile() {
        let profile = CoreVXifProfile;
        let _ = profile.issue_observation(1, 2, 3);
    }
}

pub mod ssccs_asm;
