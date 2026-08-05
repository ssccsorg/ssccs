//! SSCCS Examples - Shared utilities for experiments and examples
//!
//! This crate provides:
//! - Projector implementations (Integer, Arithmetic, Parity, CoordinateSum)
//! - Compiler pipeline for SSCCS
//! - .ss binary format parser
//! - Assembly data section emitter for the reference simulation
//! - Test helper constraints (RangeConstraint, EvenConstraint)

pub mod asm_emitter;
pub mod compiler_pipeline;
pub mod constraints;
pub mod projectors;
pub mod ss_parser;

pub use asm_emitter::*;
pub use compiler_pipeline::*;
pub use constraints::*;
pub use projectors::*;
pub use ss_parser::*;
