//! A basic space with one coordinate per axis.
use crate::core::{Segment, SpaceCoordinates};
use std::ops::Deref;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BasicSpace {
    segment: Segment,
}

impl BasicSpace {
    pub fn new(coords: SpaceCoordinates) -> Self {
        Self {
            segment: Segment::new(coords),
        }
    }

    pub fn from_segment(segment: Segment) -> Self {
        Self { segment }
    }
}

impl Deref for BasicSpace {
    type Target = Segment;

    fn deref(&self) -> &Self::Target {
        &self.segment
    }
}

impl From<SpaceCoordinates> for BasicSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self::new(coords)
    }
}

impl From<Segment> for BasicSpace {
    fn from(segment: Segment) -> Self {
        Self::from_segment(segment)
    }
}
