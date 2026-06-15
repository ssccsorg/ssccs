//! SSCCS Primitive - Core abstractions and Scheme layer
//!
//! This crate provides:
//! - The Scheme abstraction (Scheme struct, SchemeBuilder, SchemeTrait)
//! - Structural relations, constraints, and observation rules
//! - Memory layout and logical address abstractions
//!
//! Note: Concrete Scheme implementations (Grid2D, IntegerLine, etc.) are in ssccs-schemes.

pub mod scheme;
pub use scheme::*;

use ssccs_core::{Field, Projector, SegmentId};

/// Observe a Scheme through a Field using a Projector.
///
/// Returns projections for all admissible Segments in the Scheme.
/// This is the high-level API corresponding to Ω(Σ, F).
pub fn observe_scheme<P: Projector>(
    scheme: &impl SchemeTrait,
    field: &Field,
    projector: &P,
) -> Vec<P::Output> {
    scheme
        .segments()
        .filter(|segment| field.allows(segment.coordinates()))
        .filter_map(|segment| projector.project(field, segment))
        .collect()
}

/// Result of an exhaustive observation over all Segments in a Scheme.
#[derive(Debug, Clone)]
pub struct ObservationResult<P: Projector> {
    /// Total number of Segments evaluated.
    pub total: usize,
    /// Number of Segments that passed the Field constraints.
    pub admitted: usize,
    /// Number of Segments rejected by Field constraints.
    pub rejected: usize,
    /// Per-Segment results: (SegmentId, Option<projection>).
    /// None means the Segment was rejected by Field constraints.
    pub results: Vec<(SegmentId, Option<P::Output>)>,
    /// Human-readable description of the Field constraints.
    pub field_desc: String,
    /// Human-readable description of the Scheme.
    pub scheme_desc: String,
    /// Optional target name for reporting.
    pub target: String,
}

/// Exhaustively observe all Segments in a Scheme through a Field.
///
/// Iterates over every Segment in the Scheme, evaluates each against the
/// Field's constraint set, and returns an `ObservationResult` containing
/// pass/fail per Segment plus summary statistics.
///
/// This is the SSCCS-native equivalent of `ev`'s `expand_all()` + `evaluate_all()`.
pub fn observe_all<P: Projector>(
    scheme: &impl SchemeTrait,
    field: &Field,
    projector: &P,
) -> ObservationResult<P>
where
    P::Output: 'static,
{
    let mut results = Vec::new();
    let mut admitted = 0;
    for segment in scheme.segments() {
        let observation = ssccs_core::observe(field, segment, projector);
        if observation.is_some() {
            admitted += 1;
        }
        results.push((*segment.id(), observation));
    }
    let total = results.len();
    ObservationResult {
        total,
        admitted,
        rejected: total - admitted,
        results,
        field_desc: field.describe_constraints(),
        scheme_desc: scheme.describe(),
        target: String::new(),
    }
}

// ==================== TESTS ====================

#[cfg(test)]
mod tests {
    use super::*;
    use ssccs_core::{
        Coordinates, EvenConstraint, Field, LtConstraint, RangeConstraint, Segment,
        segment_id_from_coords, Projector,
    };
    use ssccs_examples::{IntegerProjector, ParityProjector};

    /// Minimal scheme stub for testing observe_all without ssccs-schemes dependency.
    #[derive(Debug)]
    struct TestScheme {
        id: crate::SchemeId,
        segments: Vec<Segment>,
    }

    impl TestScheme {
        fn new(segments: Vec<Segment>) -> Self {
            let id = crate::SchemeId(segment_id_from_coords(&Coordinates::new(vec![0])).as_bytes().clone());
            Self { id, segments }
        }
    }

    impl SchemeTrait for TestScheme {
        fn id(&self) -> &crate::SchemeId {
            &self.id
        }

        fn axes(&self) -> &[crate::Axis] {
            &[]
        }

        fn dimensionality(&self) -> usize {
            1
        }

        fn contains_segment(&self, segment_id: &ssccs_core::SegmentId) -> bool {
            self.segments.iter().any(|s| s.id() == segment_id)
        }

        fn get_segment(&self, segment_id: &ssccs_core::SegmentId) -> Option<&Segment> {
            self.segments.iter().find(|s| s.id() == segment_id)
        }

        fn segments(&self) -> Box<dyn Iterator<Item = &Segment> + '_> {
            Box::new(self.segments.iter())
        }

        fn validate_structure(&self, _coords: &Coordinates) -> Result<(), String> {
            Ok(())
        }

        fn map_to_logical_address(&self, _coords: &Coordinates) -> Option<crate::LogicalAddress> {
            None
        }

        fn describe(&self) -> String {
            format!("TestScheme({} segments)", self.segments.len())
        }
    }

    #[test]
    fn observe_all_no_constraints_all_pass() {
        let segments = vec![
            Segment::from_value(2),
            Segment::from_value(4),
            Segment::from_value(6),
        ];
        let scheme = TestScheme::new(segments);
        let field = Field::new();
        let projector = IntegerProjector::new(0);
        let result = observe_all(&scheme, &field, &projector);
        assert_eq!(result.total, 3);
        assert_eq!(result.admitted, 3);
        assert_eq!(result.rejected, 0);
    }

    #[test]
    fn observe_all_even_constraint_filters_odd() {
        let segments = vec![
            Segment::from_value(1),
            Segment::from_value(2),
            Segment::from_value(3),
            Segment::from_value(4),
        ];
        let scheme = TestScheme::new(segments);
        let mut field = Field::new();
        field.add_constraint(EvenConstraint::new(0));
        let projector = ParityProjector;
        let result = observe_all(&scheme, &field, &projector);
        assert_eq!(result.total, 4);
        assert_eq!(result.admitted, 2);
        assert_eq!(result.rejected, 2);
        for (id, obs) in &result.results {
            let seg = scheme.get_segment(id).unwrap();
            let val = seg.coordinates().get_axis(0).unwrap();
            if val % 2 == 0 {
                assert!(obs.is_some(), "even {} should pass", val);
            } else {
                assert!(obs.is_none(), "odd {} should be rejected", val);
            }
        }
    }

    #[test]
    fn observe_all_lt_constraint_rejects_above() {
        let segments = vec![
            Segment::from_value(5),
            Segment::from_value(10),
            Segment::from_value(15),
        ];
        let scheme = TestScheme::new(segments);
        let mut field = Field::new();
        field.add_constraint(LtConstraint::new(0, 12));
        let projector = IntegerProjector::new(0);
        let result = observe_all(&scheme, &field, &projector);
        assert_eq!(result.total, 3);
        assert_eq!(result.admitted, 2);
        assert_eq!(result.rejected, 1);
    }

    #[test]
    fn observe_all_summary_stats() {
        let segments = vec![
            Segment::from_value(0),
            Segment::from_value(1),
            Segment::from_value(2),
            Segment::from_value(3),
            Segment::from_value(4),
        ];
        let scheme = TestScheme::new(segments);
        let mut field = Field::new();
        field.add_constraint(RangeConstraint::new(0, 1, 3));
        let projector = IntegerProjector::new(0);
        let result = observe_all(&scheme, &field, &projector);
        assert_eq!(result.total, 5);
        assert_eq!(result.admitted, 3);
        assert_eq!(result.rejected, 2);
        assert_eq!(result.results.len(), 5);
        assert!(result.scheme_desc.contains("TestScheme"));
    }

    #[test]
    fn observe_all_empty_scheme_yields_empty_result() {
        let scheme = TestScheme::new(vec![]);
        let field = Field::new();
        let projector = IntegerProjector::new(0);
        let result = observe_all(&scheme, &field, &projector);
        assert_eq!(result.total, 0);
        assert_eq!(result.admitted, 0);
        assert_eq!(result.rejected, 0);
        assert!(result.results.is_empty());
    }

    /// A projector that always returns a fixed value.
    #[derive(Debug)]
    struct FixedProjector(i64);

    impl Projector for FixedProjector {
        type Output = i64;

        fn project(&self, _field: &Field, _segment: &Segment) -> Option<Self::Output> {
            Some(self.0)
        }
    }

    #[test]
    fn observe_all_with_custom_projector() {
        let segments = vec![
            Segment::from_value(10),
            Segment::from_value(20),
            Segment::from_value(30),
        ];
        let scheme = TestScheme::new(segments);
        let field = Field::new();
        let projector = FixedProjector(42);
        let result = observe_all(&scheme, &field, &projector);
        assert_eq!(result.admitted, 3);
        for (_, obs) in &result.results {
            assert_eq!(obs.unwrap(), 42);
        }
    }
}
