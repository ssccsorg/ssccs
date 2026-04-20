//! Developer input types - Space wrappers that add semantic meaning to Segments

#[path = "boolean.ss"]
pub mod boolean;
#[path = "integer.ss"]
pub mod integer;

pub use boolean::BooleanSpace;
pub use integer::IntegerSpace;
