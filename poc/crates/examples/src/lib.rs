//! SSCCS Examples - Shared utilities for experiments and examples
//!
//! This crate provides:
//! - Projector implementations (Integer, Arithmetic, Parity, CoordinateSum)
//! - Compiler pipeline for SSCCS
//! - .ss binary format parser
//! - Test helper constraints (RangeConstraint, EvenConstraint)

pub mod projectors;
pub mod compiler_pipeline;
pub mod ss_parser;
pub mod constraints;

pub use projectors::*;
pub use compiler_pipeline::*;
pub use ss_parser::*;
pub use constraints::*;
