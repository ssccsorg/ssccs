//! SSCCS Scheme Implementations and Developer Input Types
//!
//! This crate provides:
//! - Concrete Scheme implementations (Grid2D, IntegerLine, Graph, Tensor3D templates)
//! - Composite and Transformed Scheme extensions
//! - Developer input types (BooleanSpace, IntegerSpace)

pub mod composite;
pub mod spaces;
pub mod templates;

pub use composite::*;
pub use spaces::*;
pub use templates::*;
