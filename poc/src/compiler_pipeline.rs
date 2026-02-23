//! Compiler pipeline for SSCCS.
//!
//! Transforms a `.ss` specification into a hardware‑specific layout through a
//! deterministic pipeline:
//!
//! 1. **Parsing and Validation** – Already performed by `ss_parser`.
//! 2. **Structural Analysis** – Examines the `RelationGraph` and `StructuralConstraint`s
//!    to detect parallelism opportunities and dependencies.
//! 3. **Memory‑Layout Resolution** – Resolves the `MemoryLayout` mapping to concrete
//!    logical addresses for each Segment.
//! 4. **Hardware Mapping** – Maps logical addresses to physical resources (e.g., CPU
//!    cores, FPGA tiles, PIM units) according to a target hardware profile.
//! 5. **Observation‑Code Generation** – Produces executable code (or micro‑code) that
//!    implements the observation operator Ω for the given hardware.
//!
//! The pipeline is deterministic: given the same Scheme and hardware profile,
//! it always produces the same output.

use crate::core::SegmentId;
use crate::scheme::abstract_scheme::{LogicalAddress, Scheme};
use std::collections::HashMap;

/// Target hardware profile.
#[derive(Debug, Clone)]
pub enum HardwareProfile {
    /// Generic CPU with N cores.
    Cpu { cores: usize },
    /// FPGA with a certain number of configurable logic blocks.
    Fpga { clbs: usize },
    /// Processing‑in‑memory unit with dedicated observation logic.
    Pim { units: usize },
    /// Custom hardware description.
    Custom(String),
}

/// Result of the compilation pipeline.
#[derive(Debug)]
pub struct CompiledScheme {
    /// Original Scheme (for reference).
    pub scheme: Scheme,
    /// Mapping from SegmentId to resolved logical address.
    pub logical_addresses: HashMap<SegmentId, LogicalAddress>,
    /// Mapping from SegmentId to hardware resource.
    pub hardware_placement: HashMap<SegmentId, HardwareResource>,
    /// Generated observation code (placeholder).
    pub observation_code: Vec<u8>,
}

/// A hardware resource (core, CLB, PIM unit, etc.).
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum HardwareResource {
    CpuCore(usize),
    FpgaClb(usize),
    PimUnit(usize),
}

/// The compiler pipeline.
pub struct CompilerPipeline {
    scheme: Scheme,
    profile: HardwareProfile,
}

impl CompilerPipeline {
    /// Creates a new pipeline for the given Scheme and hardware profile.
    pub fn new(scheme: Scheme, profile: HardwareProfile) -> Self {
        Self { scheme, profile }
    }

    /// Runs the complete pipeline, returning a `CompiledScheme`.
    pub fn compile(self) -> CompiledScheme {
        let addresses = self.stage_memory_layout_resolution();
        let hardware_placement = self.stage_hardware_mapping(&addresses);
        let observation_code = self.stage_code_generation();

        CompiledScheme {
            scheme: self.scheme,
            logical_addresses: addresses,
            hardware_placement,
            observation_code,
        }
    }

    /// Stage 3: Memory‑Layout Resolution.
    /// Uses the Scheme's `MemoryLayout` to compute a logical address for each Segment.
    fn stage_memory_layout_resolution(&self) -> HashMap<SegmentId, LogicalAddress> {
        let mut addresses = HashMap::new();
        for segment in self.scheme.segments() {
            let coords = segment.coordinates();
            if let Some(addr) = self.scheme.map_to_logical_address(coords) {
                addresses.insert(*segment.id(), addr);
            }
        }
        addresses
    }

    /// Stage 4: Hardware Mapping.
    /// Maps logical addresses to concrete hardware resources according to the profile.
    fn stage_hardware_mapping(
        &self,
        addresses: &HashMap<SegmentId, LogicalAddress>,
    ) -> HashMap<SegmentId, HardwareResource> {
        let mut placement = HashMap::new();
        match &self.profile {
            HardwareProfile::Cpu { cores } => {
                // Simple round‑robin assignment across cores.
                for (idx, (segment_id, _)) in addresses.iter().enumerate() {
                    let core = idx % cores;
                    placement.insert(*segment_id, HardwareResource::CpuCore(core));
                }
            }
            HardwareProfile::Fpga { clbs } => {
                // Place each Segment in a separate CLB (simplistic).
                for (idx, (segment_id, _)) in addresses.iter().enumerate() {
                    let clb = idx % clbs;
                    placement.insert(*segment_id, HardwareResource::FpgaClb(clb));
                }
            }
            HardwareProfile::Pim { units } => {
                for (idx, (segment_id, _)) in addresses.iter().enumerate() {
                    let unit = idx % units;
                    placement.insert(*segment_id, HardwareResource::PimUnit(unit));
                }
            }
            HardwareProfile::Custom(_) => {
                // No mapping.
            }
        }
        placement
    }

    /// Stage 5: Observation‑Code Generation.
    /// Generates placeholder code (in reality this would produce machine code,
    /// FPGA bitstream, or PIM micro‑code).
    fn stage_code_generation(&self) -> Vec<u8> {
        // Placeholder: empty byte vector.
        vec![]
    }
}
