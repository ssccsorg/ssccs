//! Arithmetic state space
use crate::{SchemeSegment, SpaceCoordinates};

#[derive(Debug, Clone, Eq, PartialEq, Hash)]
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

    fn basic_adjacency(&self) -> Vec<SpaceCoordinates> {
        let current = self.coords.get_axis(0).unwrap_or(0);

        vec![
            SpaceCoordinates::new(vec![current + 1]), // +1
            SpaceCoordinates::new(vec![current - 1]), // 1
            SpaceCoordinates::new(vec![current * 2]), // ×2
            SpaceCoordinates::new(vec![current / 2]), // ÷2 (integer)
        ]
    }
}

impl From<SpaceCoordinates> for ArithmeticSpace {
    fn from(coords: SpaceCoordinates) -> Self {
        Self { coords }
    }
}
