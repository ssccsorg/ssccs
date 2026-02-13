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
/// both the segment's intrinsic adjacency and the field's transition matrix,
/// filtered by field constraints.
pub fn possible_next_coordinates(
    field: &Field,
    segment: &dyn SchemeSegment,
) -> Vec<SpaceCoordinates> {
    let current = segment.coordinates();
    let mut candidates = segment.basic_adjacency();
    candidates.extend(field.transition_targets(&current));
    candidates.retain(|c| field.allows(c));
    candidates
}

/// Recursively explore the state space up to a given depth (demo only – not a core concept).
/// Returns the set of all projection values encountered.
/// Note: depth is a demo parameter; in a true SSCCS system, time is just another coordinate.
///
/// This function requires a way to reconstruct a `SchemeSegment` from `SpaceCoordinates`.
/// For demonstration, you must provide a closure `make_segment` that does this.
pub fn observe_tree<P, F>(
    field: &Field,
    start_coords: SpaceCoordinates,
    projector: &P,
    make_segment: F,
    max_depth: usize,
) -> std::collections::HashSet<P::Output>
where
    P: Projector,
    P::Output: Eq + std::hash::Hash,
    F: Fn(SpaceCoordinates) -> Box<dyn SchemeSegment>,
{
    let mut results = std::collections::HashSet::new();
    let mut visited = std::collections::HashSet::new();
    let mut stack = vec![(start_coords, 0)];

    while let Some((coords, depth)) = stack.pop() {
        if !visited.insert(coords.clone()) {
            continue;
        }

        let segment = make_segment(coords.clone());
        if let Some(proj) = observe(field, segment.as_ref(), projector) {
            results.insert(proj);
        }

        if depth >= max_depth {
            continue;
        }

        // Compute next coordinates using a temporary segment (just to get basic adjacency)
        // We need the segment's basic adjacency, so we create one via the closure.
        let temp_seg = make_segment(coords);
        let next = possible_next_coordinates(field, temp_seg.as_ref());
        for n in next {
            if !visited.contains(&n) {
                stack.push((n, depth + 1));
            }
        }
    }

    results
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
