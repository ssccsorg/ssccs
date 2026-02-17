//! An integer space: single‑axis.
use crate::core::{SchemeSegment, SpaceCoordinates};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct IntegerSpace {
    coords: SpaceCoordinates,
}

impl IntegerSpace {
    pub fn new(value: i64) -> Self {
        Self {
            coords: SpaceCoordinates::new(vec![value]),
        }
    }
}

impl SchemeSegment for IntegerSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coords.clone()
    }
}

impl From<SpaceCoordinates> for IntegerSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self { coords }
    }
}
