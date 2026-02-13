//! A basic space with one coordinate per axis and simple ±1 adjacency.
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

    fn basic_adjacency(&self) -> Vec<SpaceCoordinates> {
        let mut adjacent = Vec::new();
        let dim = self.coords.dimensionality();

        for i in 0..dim {
            if let Some(val) = self.coords.get_axis(i) {
                let mut plus = self.coords.raw.clone();
                plus[i] = val + 1;
                adjacent.push(SpaceCoordinates::new(plus));

                let mut minus = self.coords.raw.clone();
                minus[i] = val - 1;
                adjacent.push(SpaceCoordinates::new(minus));
            }
        }

        adjacent
    }
}

impl From<SpaceCoordinates> for BasicSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self::new(coords)
    }
}
