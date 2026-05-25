//! Developer input types - Space wrappers that add semantic meaning to Segments

// The IDE may show "unresolved module" for #[path = "*.ss"];
// this is harmless — build.rs resolves .ss files at build time.
#![allow(unused_attributes)]

#[path = "boolean.ss"]
pub mod boolean;
#[path = "integer.ss"]
pub mod integer;

pub use boolean::BooleanSpace;
pub use integer::IntegerSpace;
