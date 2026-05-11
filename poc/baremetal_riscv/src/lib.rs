//! SSCCS hardware integration library.
//! Provides primitives for observing SSCCS Schemas via custom RISC-V instructions
//! and interfaces with the OpenHW CORE-V XIF coprocessor.

#![cfg_attr(not(test), no_std)]

#[cfg(not(test))]
use panic_halt as _;

pub mod instructions;

/// Hardware profile for OpenHW CORE-V XIF.
pub struct CoreVXifProfile;

impl CoreVXifProfile {
    /// Maximum number of source registers supported by XIF.
    pub const X_NUM_RS: usize = 3;

    /// Issue an observation via XIF interface.
    /// This is a stub for future hardware implementation.
    pub fn issue_observation(&self, scheme_id: u32, field_id: u32, rule_id: u32) -> u32 {
        // Placeholder: In real hardware, this would trigger XIF signals.
        // For now, delegate to software emulation.
        instructions::observe_emulate(scheme_id, field_id, rule_id)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

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
