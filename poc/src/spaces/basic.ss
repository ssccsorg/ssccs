//! A basic space with one coordinate per axis.
use crate::core::{SchemeSegment, SpaceCoordinates};

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct BasicSpace {
    coords: SpaceCoordinates,
}

impl BasicSpace {
    pub fn new(coords: SpaceCoordinates) -> Self {
        Self { coords }
    }
}

impl SchemeSegment for BasicSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coords.clone()
    }
}

impl From<SpaceCoordinates> for BasicSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self::new(coords)
    }
}