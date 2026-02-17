pub mod core;
use crate::core::{Constraint, Field, Projector, SchemeSegment, SpaceCoordinates};
use std::fmt::Debug;

// ==================== CONSTRAINT IMPLEMENTATIONS ====================

/// Constraint that an axis must lie within a given inclusive range.
#[derive(Debug, Clone)]
pub struct RangeConstraint {
    axis: usize,
    min: i64,
    max: i64,
}

impl RangeConstraint {
    pub fn new(axis: usize, min: i64, max: i64) -> Self {
        Self { axis, min, max }
    }
}

impl Constraint for RangeConstraint {
    fn allows(&self, coords: &SpaceCoordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v >= self.min && v <= self.max)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] ∈ [{}, {}]", self.axis, self.min, self.max)
    }
}

/// Constraint that an axis must be even.
#[derive(Debug, Clone)]
pub struct EvenConstraint {
    axis: usize,
}

impl EvenConstraint {
    pub fn new(axis: usize) -> Self {
        Self { axis }
    }
}

impl Constraint for EvenConstraint {
    fn allows(&self, coords: &SpaceCoordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v % 2 == 0)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] is even", self.axis)
    }
}

// ==================== OBSERVATION FUNCTIONS ====================

/// Observe a single point: project if the coordinate is allowed by the field.
pub fn observe<P: Projector>(
    field: &Field,
    segment: &dyn SchemeSegment,
    projector: &P,
) -> Option<P::Output> {
    if field.allows(&segment.coordinates()) {
        projector.project(field, segment)
    } else {
        None
    }
}

/// Compute all possible next coordinates from the current segment, taking into account
/// both the projector's interpretation of adjacency and the field's transition matrix,
/// filtered by field constraints.
pub fn possible_next_coordinates<P: Projector>(
    field: &Field,
    segment: &dyn SchemeSegment,
    projector: &P,
) -> Vec<SpaceCoordinates> {
    let current = segment.coordinates();
    let mut candidates = projector.possible_next_coordinates(&current);
    candidates.extend(field.transition_targets(&current));
    candidates.retain(|c| field.allows(c));
    candidates
}

// ==================== MODULE STRUCTURE ====================

pub mod spaces {
    // Arithmetic.ss
    #[path = "../spaces/arithmetic.ss"]
    pub mod arithmetic;

    // Basic.ss
    #[path = "../spaces/basic.ss"]
    pub mod basic;
}
pub use spaces::*;