use ssccs_poc::core::{Field, Projector, Segment, SpaceCoordinates};

#[derive(Debug, Clone)]
pub struct IntegerProjector {
    axis: usize,
}

impl IntegerProjector {
    pub fn new(axis: usize) -> Self {
        Self { axis }
    }
}

impl Projector for IntegerProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(self.axis)
    }

    // No intrinsic adjacency for this projector.
}

// A projector that performs arithmetic operations to generate neighbours.
#[derive(Debug, Clone)]
pub struct ArithmeticProjector;

impl Projector for ArithmeticProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(0)
    }

    fn possible_next_coordinates(&self, coords: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        let current = coords.get_axis(0).unwrap_or(0);
        vec![
            SpaceCoordinates::new(vec![current + 1]),
            SpaceCoordinates::new(vec![current - 1]),
            SpaceCoordinates::new(vec![current * 2]),
            SpaceCoordinates::new(vec![current / 2]), // integer division
        ]
    }
}

// A projector that returns a string based on parity.
#[derive(Debug, Clone)]
pub struct ParityProjector;

impl Projector for ParityProjector {
    type Output = String;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let coord = segment.coordinates().get_axis(0)?;
        if coord % 2 == 0 {
            Some("even".into())
        } else {
            Some("odd".into())
        }
    }
}
