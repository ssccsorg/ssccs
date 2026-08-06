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

use crate::asm_emitter::emit_scheme_data;
use crate::constraint_emitter::{ConstraintSpec, emit_constraint_gates};
use ssccs_core::{Segment, SegmentId};
use ssccs_primitive::scheme::abstract_scheme::{LogicalAddress, Scheme};
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
    /// Declared Field constraint gates, emitted alongside the scheme data.
    field_specs: Vec<(String, ConstraintSpec)>,
}

impl CompilerPipeline {
    /// Creates a new pipeline for the given Scheme and hardware profile.
    pub fn new(scheme: Scheme, profile: HardwareProfile) -> Self {
        Self {
            scheme,
            profile,
            field_specs: Vec::new(),
        }
    }

    /// Declares the Field constraint gates to emit alongside the scheme
    /// data. Each entry pairs an assembly label with a constraint spec;
    /// labels must be valid assembly symbols and unique. The emitted gates
    /// are drop-in `field_fn` values for the observation routines.
    pub fn with_constraints(mut self, specs: Vec<(&str, ConstraintSpec)>) -> Self {
        self.field_specs = specs
            .into_iter()
            .map(|(label, spec)| (label.to_string(), spec))
            .collect();
        self
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

    /// Stage 5: Observation-Code Generation.
    /// Emits the Scheme structure as an assembly `.rodata` data section:
    /// segment coordinate tables, logical address tables, and golden anchor
    /// comments, followed by the declared branchless constraint gates in
    /// `.text`. The observation routines of the reference simulation
    /// consume this baked structure directly.
    fn stage_code_generation(&self) -> Vec<u8> {
        let mut out = emit_scheme_data(&self.scheme).text;
        if !self.field_specs.is_empty() {
            out.push('\n');
            out.push_str(&emit_constraint_gates(
                &self.field_specs,
                &self.gate_fixture(),
            ));
        }
        out.into_bytes()
    }

    /// The fixture for gate golden anchors: the sorted axis-0 values of
    /// the scheme's segments, matching the emitted structure tables.
    fn gate_fixture(&self) -> Vec<i64> {
        let mut segments: Vec<&Segment> = self.scheme.segments().collect();
        segments.sort_by(|a, b| a.coordinates().raw.cmp(&b.coordinates().raw));
        segments
            .iter()
            .map(|s| s.coordinates().raw.first().copied().unwrap_or(0))
            .collect()
    }
}
