//! SSCCS Examples - Shared utilities for experiments and examples
//!
//! This crate provides:
//! - Projector implementations (Integer, Arithmetic, Parity, CoordinateSum)
//! - Compiler pipeline for SSCCS
//! - .ss binary format parser
//! - Test helper constraints (RangeConstraint, EvenConstraint)

pub mod compiler_pipeline;
pub mod constraints;
pub mod projectors;
pub mod ss_parser;

pub use compiler_pipeline::*;
pub use constraints::*;
pub use projectors::*;
pub use ss_parser::*;
