//! 기본 상태 공간
use crate::{SchemeSegment, SpaceCoordinates};

#[derive(Debug, Clone, Eq, PartialEq, Hash)]
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
                // +1 방향
                let mut plus = self.coords.raw.clone();
                plus[i] = val + 1;
                adjacent.push(SpaceCoordinates::new(plus));

                // -1 방향
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
        Self { coords }
    }
}
