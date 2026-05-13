//! SSCCS Primitive - Core abstractions and Scheme layer
//!
//! This crate provides:
//! - The Scheme abstraction (Scheme struct, SchemeBuilder, SchemeTrait)
//! - Structural relations, constraints, and observation rules
//! - Memory layout and logical address abstractions
//!
//! Note: Concrete Scheme implementations (Grid2D, IntegerLine, etc.) are in ssccs-schemes.

pub mod scheme;
pub use scheme::*;

use ssccs_core::{Field, Projector};

/// Observe a Scheme through a Field using a Projector.
///
/// Returns projections for all admissible Segments in the Scheme.
/// This is the high-level API corresponding to Ω(Σ, F).
pub fn observe_scheme<P: Projector>(
    scheme: &impl SchemeTrait,
    field: &Field,
    projector: &P,
) -> Vec<P::Output> {
    scheme
        .segments()
        .filter(|segment| field.allows(segment.coordinates()))
        .filter_map(|segment| projector.project(field, segment))
        .collect()
}
