//! Composite and Transformed Scheme extensions.
//!
//! Re-exports composite scheme types from ssccs-primitive,
//! which hosts the canonical definitions used by SchemeImpl.

pub use ssccs_primitive::{
    AlignmentRules, CombinationMethod, CompositeScheme, CompositionRules,
    ConflictResolution, Matrix, TransformType, Transformation, TransformedScheme,
};
