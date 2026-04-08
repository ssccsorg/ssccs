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
