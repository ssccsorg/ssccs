//! Determinism and race-freedom validation for the reference simulation.
//!
//! The model defines determinism, statelessness, and implicit parallelism
//! as properties of the observation operator. These tests verify the
//! properties mechanically on the host path: repeated observations always
//! reproduce the same projection, and concurrent observations on disjoint
//! regions reproduce the sequential baseline without locks.

use ssccs_core::{Field, Segment, observe};
use ssccs_examples::constraints::{EvenConstraint, RangeConstraint};
use ssccs_examples::projectors::{CoordinateSumProjector, IntegerProjector};
use ssccs_primitive::scheme::abstract_scheme::{Axis, AxisType, Scheme, SchemeBuilder};
use std::thread;

/// The reject sentinel, matching `baremetal_riscv` `REJECT_SENTINEL`.
const REJECT: i64 = i64::MIN;

/// Integer line scheme mirroring the `observe_full.S` fixture.
fn integer_line_scheme() -> Scheme {
    let mut builder = SchemeBuilder::new().add_axis(Axis {
        name: "x".to_string(),
        axis_type: AxisType::Discrete,
        metadata: Default::default(),
    });
    for v in [2i64, 3, 5, 10, 12] {
        builder = builder.add_segment(&Segment::from_values(vec![v]));
    }
    builder.build()
}

/// 3x3 grid scheme with a segment at every (x, y).
fn grid3x3_scheme() -> Scheme {
    let mut builder = SchemeBuilder::new()
        .add_axis(Axis {
            name: "x".to_string(),
            axis_type: AxisType::Discrete,
            metadata: Default::default(),
        })
        .add_axis(Axis {
            name: "y".to_string(),
            axis_type: AxisType::Discrete,
            metadata: Default::default(),
        });
    for x in 0..3i64 {
        for y in 0..3i64 {
            builder = builder.add_segment(&Segment::from_values(vec![x, y]));
        }
    }
    builder.build()
}

/// Sorted segments of a scheme, matching the emitter's deterministic order.
fn sorted_segments(scheme: &Scheme) -> Vec<&Segment> {
    let mut segments: Vec<&Segment> = scheme.segments().collect();
    segments.sort_by(|a, b| a.coordinates().raw.cmp(&b.coordinates().raw));
    segments
}

/// Narrow field: even on axis 0 AND range [0,10] on axis 0.
fn narrow_field() -> Field {
    let mut field = Field::new();
    field.add_constraint(EvenConstraint::new(0));
    field.add_constraint(RangeConstraint::new(0, 0, 10));
    field
}

#[test]
fn repeated_observation_is_deterministic() {
    let scheme = integer_line_scheme();
    let field = narrow_field();
    let projector = IntegerProjector::new(0);
    let segments = sorted_segments(&scheme);

    let expected = [2, REJECT, REJECT, 10, REJECT];
    for _ in 0..1000 {
        let results: Vec<i64> = segments
            .iter()
            .map(|s| observe(&field, s, &projector).unwrap_or(REJECT))
            .collect();
        assert_eq!(results, expected);
    }
}

#[test]
fn observation_is_deterministic_across_reconstruction() {
    let forward = integer_line_scheme();
    let mut builder = SchemeBuilder::new().add_axis(Axis {
        name: "x".to_string(),
        axis_type: AxisType::Discrete,
        metadata: Default::default(),
    });
    for v in [12i64, 10, 5, 3, 2] {
        builder = builder.add_segment(&Segment::from_values(vec![v]));
    }
    let reversed = builder.build();

    let field = narrow_field();
    let projector = IntegerProjector::new(0);
    let observe_all = |scheme: &Scheme| {
        sorted_segments(scheme)
            .iter()
            .map(|s| observe(&field, s, &projector).unwrap_or(REJECT))
            .collect::<Vec<i64>>()
    };
    assert_eq!(observe_all(&forward), observe_all(&reversed));
}

#[test]
fn concurrent_disjoint_observation_matches_sequential() {
    let scheme = grid3x3_scheme();
    let mut field = Field::new();
    field.add_constraint(EvenConstraint::new(0));
    field.add_constraint(RangeConstraint::new(1, 0, 2));
    let projector = CoordinateSumProjector;

    let segments = sorted_segments(&scheme);
    let baseline: Vec<i64> = segments
        .iter()
        .map(|s| observe(&field, s, &projector).unwrap_or(REJECT))
        .collect();

    // Partition into three disjoint regions by column (axis 0): each
    // region is observed on its own thread, with no locks and no shared
    // mutable state. Segments are immutable, so the concurrent results
    // must reproduce the sequential baseline exactly.
    let group_indices: Vec<Vec<usize>> = (0..3)
        .map(|x| {
            segments
                .iter()
                .enumerate()
                .filter(|(_, s)| s.coordinates().get_axis(0) == Some(x))
                .map(|(i, _)| i)
                .collect()
        })
        .collect();
    let groups: Vec<Vec<&Segment>> = (0..3)
        .map(|x| {
            segments
                .iter()
                .filter(|s| s.coordinates().get_axis(0) == Some(x))
                .cloned()
                .collect()
        })
        .collect();

    thread::scope(|scope| {
        let field = &field;
        let projector = &projector;
        let handles: Vec<_> = groups
            .into_iter()
            .map(|group| {
                scope.spawn(move || {
                    group
                        .iter()
                        .map(|s| observe(field, s, projector).unwrap_or(REJECT))
                        .collect::<Vec<i64>>()
                })
            })
            .collect();

        for (handle, indices) in handles.into_iter().zip(&group_indices) {
            let results = handle.join().expect("observation thread");
            assert_eq!(results.len(), indices.len());
            for (idx, result) in indices.iter().zip(results) {
                assert_eq!(baseline[*idx], result, "segment index {idx}");
            }
        }
    });
}

#[test]
fn concurrent_observation_is_repeatable() {
    let scheme = grid3x3_scheme();
    let mut field = Field::new();
    field.add_constraint(EvenConstraint::new(0));
    field.add_constraint(RangeConstraint::new(1, 0, 2));
    let projector = CoordinateSumProjector;

    let segments = sorted_segments(&scheme);
    let baseline: Vec<i64> = segments
        .iter()
        .map(|s| observe(&field, s, &projector).unwrap_or(REJECT))
        .collect();

    for _ in 0..10 {
        let groups: Vec<Vec<&Segment>> = (0..3)
            .map(|x| {
                segments
                    .iter()
                    .filter(|s| s.coordinates().get_axis(0) == Some(x))
                    .cloned()
                    .collect()
            })
            .collect();
        let field = &field;
        let projector = &projector;
        let concurrent: Vec<i64> = thread::scope(|scope| {
            let handles: Vec<_> = groups
                .into_iter()
                .map(|group| {
                    scope.spawn(move || {
                        group
                            .iter()
                            .map(|s| observe(field, s, projector).unwrap_or(REJECT))
                            .collect::<Vec<i64>>()
                    })
                })
                .collect();
            handles
                .into_iter()
                .flat_map(|h| h.join().expect("observation thread"))
                .collect()
        });
        let mut concurrent_sorted = concurrent;
        concurrent_sorted.sort();
        let mut baseline_sorted = baseline.clone();
        baseline_sorted.sort();
        assert_eq!(concurrent_sorted, baseline_sorted);
    }
}
