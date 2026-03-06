//! A boolean space: single‑axis with true/false values.
//!
//! Represents boolean values as 1D coordinates:
//! - false → coordinate [0]
//! - true  → coordinate [1]
use crate::core::{Segment, SpaceCoordinates};
use std::ops::Deref;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BooleanSpace {
    segment: Segment,
}

impl BooleanSpace {
    /// Create a new BooleanSpace from a boolean value.
    pub fn new(value: bool) -> Self {
        let coord = if value { 1 } else { 0 };
        Self {
            segment: Segment::from_value(coord),
        }
    }

    /// Create a BooleanSpace from an existing Segment.
    /// The segment must be 1‑dimensional.
    pub fn from_segment(segment: Segment) -> Self {
        Self { segment }
    }

    /// Get the boolean value represented by this space.
    /// Returns true if the coordinate is non‑zero, false otherwise.
    pub fn value(&self) -> bool {
        self.segment.coordinates().raw[0] != 0
    }
}

impl Deref for BooleanSpace {
    type Target = Segment;

    fn deref(&self) -> &Self::Target {
        &self.segment
    }
}

impl From<SpaceCoordinates> for BooleanSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        // Convert first coordinate to boolean (non‑zero = true)
        let value = coords.raw.first().map(|&v| v != 0).unwrap_or(false);
        Self::new(value)
    }
}

impl From<Segment> for BooleanSpace {
    fn from(segment: Segment) -> Self {
        Self::from_segment(segment)
    }
}

impl From<bool> for BooleanSpace {
    fn from(value: bool) -> Self {
        Self::new(value)
    }
}
