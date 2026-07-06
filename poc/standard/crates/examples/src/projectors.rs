//! Projector implementations for SSCCS examples and experiments.

use ssccs_core::{Coordinates, Field, Projector, Segment};

/// A projector that extracts a coordinate along a given axis.
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

/// A projector that performs arithmetic operations to generate neighbours.
#[derive(Debug, Clone)]
pub struct ArithmeticProjector;

impl Projector for ArithmeticProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(0)
    }

    fn possible_next_coordinates(&self, coords: &Coordinates) -> Vec<Coordinates> {
        let current = coords.get_axis(0).unwrap_or(0);
        vec![
            Coordinates::new(vec![current + 1]),
            Coordinates::new(vec![current - 1]),
            Coordinates::new(vec![current * 2]),
            Coordinates::new(vec![current / 2]), // integer division
        ]
    }
}

/// A projector that returns a string based on parity.
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

/// A projector that sums coordinates for 3D tensor.
#[derive(Debug, Clone)]
pub struct CoordinateSumProjector;

impl Projector for CoordinateSumProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let coords = segment.coordinates();
        let sum = coords.get_axis(0).unwrap_or(0)
            + coords.get_axis(1).unwrap_or(0)
            + coords.get_axis(2).unwrap_or(0);
        Some(sum)
    }
}

// ====================================================================
// Operator Projectors — mapped from nex-calc's OpType (nexus PR #143)
//
// nex-calc proved F × I × H → F' on 23 operators. These projectors
// bring the arithmetic subset into SSCCS core for scenario testing.
// ====================================================================

/// Projector: remainder (a % b). b ≠ 0 required.
#[derive(Debug, Clone)]
pub struct RemProjector(pub i64); // divisor

impl Projector for RemProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        if self.0 == 0 { None } else { Some(a % self.0) }
    }
}

/// Projector: power (a ^ exp). exp ≥ 0, no overflow.
#[derive(Debug, Clone)]
pub struct PowProjector(pub u32);

impl Projector for PowProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        a.checked_pow(self.0)
    }
}

/// Projector: minimum of axis 0 and axis 1.
#[derive(Debug, Clone)]
pub struct MinProjector;

impl Projector for MinProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        let b = segment.coordinates().get_axis(1)?;
        Some(a.min(b))
    }
}

/// Projector: maximum of axis 0 and axis 1.
#[derive(Debug, Clone)]
pub struct MaxProjector;

impl Projector for MaxProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        let b = segment.coordinates().get_axis(1)?;
        Some(a.max(b))
    }
}

/// Projector: absolute value of axis 0.
#[derive(Debug, Clone)]
pub struct AbsProjector;

impl Projector for AbsProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(0).map(|a| a.abs())
    }
}

/// Projector: negation of axis 0.
#[derive(Debug, Clone)]
pub struct NegProjector;

impl Projector for NegProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(0).and_then(|a| a.checked_neg())
    }
}

/// Projector: bitwise AND of axis 0 and axis 1.
#[derive(Debug, Clone)]
pub struct BitAndProjector;

impl Projector for BitAndProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        let b = segment.coordinates().get_axis(1)?;
        Some(a & b)
    }
}

/// Projector: bitwise OR of axis 0 and axis 1.
#[derive(Debug, Clone)]
pub struct BitOrProjector;

impl Projector for BitOrProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        let b = segment.coordinates().get_axis(1)?;
        Some(a | b)
    }
}

/// Projector: bitwise XOR of axis 0 and axis 1.
#[derive(Debug, Clone)]
pub struct BitXorProjector;

impl Projector for BitXorProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let a = segment.coordinates().get_axis(0)?;
        let b = segment.coordinates().get_axis(1)?;
        Some(a ^ b)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ssccs_core::Field;

    #[test]
    fn test_rem() {
        let p = RemProjector(3);
        let seg = Segment::from_value(10);
        assert_eq!(p.project(&Field::new(), &seg), Some(1));
    }

    #[test]
    fn test_pow() {
        let p = PowProjector(3);
        let seg = Segment::from_value(2);
        assert_eq!(p.project(&Field::new(), &seg), Some(8));
    }

    #[test]
    fn test_min_max() {
        let seg = Segment::new(Coordinates::new(vec![3, 7]));
        assert_eq!(MinProjector.project(&Field::new(), &seg), Some(3));
        assert_eq!(MaxProjector.project(&Field::new(), &seg), Some(7));
    }

    #[test]
    fn test_abs() {
        let seg = Segment::from_value(-5);
        assert_eq!(AbsProjector.project(&Field::new(), &seg), Some(5));
    }

    #[test]
    fn test_neg() {
        let seg = Segment::from_value(42);
        assert_eq!(NegProjector.project(&Field::new(), &seg), Some(-42));
    }

    #[test]
    fn test_bitwise() {
        let seg = Segment::new(Coordinates::new(vec![6, 3]));
        assert_eq!(BitAndProjector.project(&Field::new(), &seg), Some(2)); // 110 & 011 = 010
        assert_eq!(BitOrProjector.project(&Field::new(), &seg), Some(7));  // 110 | 011 = 111
        assert_eq!(BitXorProjector.project(&Field::new(), &seg), Some(5)); // 110 ^ 011 = 101
    }
}
