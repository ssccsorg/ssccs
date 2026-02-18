//! An integer space: single‑axis.
use crate::core::{Segment, SpaceCoordinates};
use std::ops::Deref;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct IntegerSpace {
    segment: Segment,
}

impl IntegerSpace {
    pub fn new(value: i64) -> Self {
        Self {
            segment: Segment::from_value(value),
        }
    }

    pub fn from_segment(segment: Segment) -> Self {
        Self { segment }
    }
}

impl Deref for IntegerSpace {
    type Target = Segment;

    fn deref(&self) -> &Self::Target {
        &self.segment
    }
}

impl From<SpaceCoordinates> for IntegerSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self {
            segment: Segment::new(coords),
        }
    }
}

impl From<Segment> for IntegerSpace {
    fn from(segment: Segment) -> Self {
        Self::from_segment(segment)
    }
}
