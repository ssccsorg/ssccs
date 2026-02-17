//! An arithmetic space: single‑axis.
use crate::core::{SchemeSegment, SpaceCoordinates};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct ArithmeticSpace {
    coords: SpaceCoordinates,
}

impl ArithmeticSpace {
    pub fn new(value: i64) -> Self {
        Self {
            coords: SpaceCoordinates::new(vec![value]),
        }
    }
}

impl SchemeSegment for ArithmeticSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coords.clone()
    }
}

impl From<SpaceCoordinates> for ArithmeticSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self { coords }
    }
}
