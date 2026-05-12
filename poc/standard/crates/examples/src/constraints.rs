//! Test helper constraints for experiments.

use ssccs_core::{Constraint, Coordinates};

/// A constraint that requires a coordinate axis to be within a range.
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
    fn allows(&self, coords: &Coordinates) -> bool {
        if let Some(value) = coords.get_axis(self.axis) {
            value >= self.min && value <= self.max
        } else {
            false
        }
    }

    fn describe(&self) -> String {
        format!("axis {} in [{}, {}]", self.axis, self.min, self.max)
    }
}

/// A constraint that requires a coordinate axis to be even.
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
    fn allows(&self, coords: &Coordinates) -> bool {
        if let Some(value) = coords.get_axis(self.axis) {
            value % 2 == 0
        } else {
            false
        }
    }

    fn describe(&self) -> String {
        format!("axis {} is even", self.axis)
    }
}
