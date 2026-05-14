use std::sync::Arc;

use ssccs_core::{Coordinates, Field, Segment};
use ssccs_examples::{CoordinateSumProjector, EvenConstraint, RangeConstraint};
use ssccs_field_synthesis::{compose_observe, intersection, union};

/// A self-contained demonstration that Field composition changes what is observable.
pub trait Scenario {
    fn name(&self) -> &'static str;
    fn run(&self);
}

/// All registered scenarios.
pub fn registry() -> Vec<Box<dyn Scenario>> {
    vec![Box::new(Grid2D {}), Box::new(SensorTimeTemp {})]
}

// ==================== GRID 2D ====================

struct Grid2D;

impl Scenario for Grid2D {
    fn name(&self) -> &'static str {
        "Grid2D: Parity × Range"
    }

    fn run(&self) {
        let mut p_field = Field::new();
        p_field.add_constraint(EvenConstraint::new(0));
        let p = Arc::new(p_field);
        let mut q_field = Field::new();
        q_field.add_constraint(RangeConstraint::new(1, 0, 1));
        let q = Arc::new(q_field);

        let segs: Vec<Segment> = (0..=2)
            .flat_map(|y| (0..=2).map(move |x| Segment::new(Coordinates::new(vec![x, y]))))
            .collect();
        assert_eq!(segs.len(), 9);

        let narrow = intersection(p.clone(), q.clone());
        let narrow_count = segs
            .iter()
            .filter(|s| narrow.allows(s.coordinates()))
            .count();
        assert_eq!(narrow_count, 4);

        let broad = union(p.clone(), q.clone());
        let broad_count = segs
            .iter()
            .filter(|s| broad.allows(s.coordinates()))
            .count();
        assert_eq!(broad_count, 8);

        let proj = CoordinateSumProjector;
        let sums: Vec<i64> = segs
            .iter()
            .filter_map(|s| compose_observe(&narrow, &proj, s))
            .collect();
        assert_eq!(sums, vec![0, 2, 1, 3]);

        let broad_sums: Vec<i64> = segs
            .iter()
            .filter_map(|s| compose_observe(&broad, &proj, s))
            .collect();
        assert_eq!(broad_sums.len(), 8);

        println!("    axis[0]=parity  axis[1]=range  9-segment 2D space");
        println!(
            "    P∩Q (narrow): {} segments → sums: {:?}",
            narrow_count, sums
        );
        println!("    P∪Q (broad):  {} segments", broad_count);
    }
}

// ==================== SENSOR × TIME × TEMPERATURE ====================

/// Heterogeneous axes — each carries a distinct physical meaning.
///
/// - axis[0]: time step   (0=early, 1=mid, 2=late)
/// - axis[1]: sensor id   (0, 1)
/// - axis[2]: temperature (0=low, 1=medium, 2=high)
///
/// Fields represent domain questions applied to this 3D observation space.
struct SensorTimeTemp;

impl Scenario for SensorTimeTemp {
    fn name(&self) -> &'static str {
        "Sensor×Time×Temperature"
    }

    fn run(&self) {
        // ── axes ──
        // time: 0..=2 (3 steps), sensor: 0..=1 (2 ids), temp: 0..=2 (3 bands)
        // Total segments: 3 × 2 × 3 = 18

        let segs: Vec<Segment> = (0..=2)
            .flat_map(|t| {
                (0..=1).flat_map(move |s| {
                    (0..=2).map(move |c| Segment::new(Coordinates::new(vec![t, s, c])))
                })
            })
            .collect();
        assert_eq!(segs.len(), 18);

        // ── domain Fields ──
        // "early time"       : axis[0] ∈ [0, 1]
        // "sensor 0 only"    : axis[1] = 0
        // "high temperature" : axis[2] ∈ [2, 2]  (only band 2)

        let mut early_time_field = Field::new();
        early_time_field.add_constraint(RangeConstraint::new(0, 0, 1));
        let early_time = Arc::new(early_time_field);

        let mut sensor_zero_field = Field::new();
        sensor_zero_field.add_constraint(RangeConstraint::new(1, 0, 0));
        let sensor_zero = Arc::new(sensor_zero_field);

        let mut high_temp_field = Field::new();
        high_temp_field.add_constraint(RangeConstraint::new(2, 2, 2));
        let high_temp = Arc::new(high_temp_field);

        // ── inquiry compositions ──
        // Narrow: early time ∧ sensor 0 ∧ high temp → very specific
        let narrow = intersection(
            intersection(early_time.clone(), sensor_zero.clone()),
            high_temp.clone(),
        );
        // Broad: early time ∨ sensor 0 ∨ high temp → exploratory
        let broad = union(
            union(early_time.clone(), sensor_zero.clone()),
            high_temp.clone(),
        );
        // Mixed: (early time ∧ sensor 0) ∨ high temp → relax temperature
        let mixed = union(
            intersection(early_time.clone(), sensor_zero.clone()),
            high_temp.clone(),
        );

        let proj = CoordinateSumProjector;

        let narrow_results: Vec<i64> = segs
            .iter()
            .filter_map(|s| compose_observe(&narrow, &proj, s))
            .collect();
        let broad_results: Vec<i64> = segs
            .iter()
            .filter_map(|s| compose_observe(&broad, &proj, s))
            .collect();
        let mixed_results: Vec<i64> = segs
            .iter()
            .filter_map(|s| compose_observe(&mixed, &proj, s))
            .collect();

        // Verify counts manually:
        // Narrow: t∈{0,1} ∩ s=0 ∩ c=2 → 2×1×1 = 2
        assert_eq!(narrow_results.len(), 2);
        // Broad: NOT (t=2 ∧ s=1 ∧ c∈{0,1}) → 18 - 2 = 16
        assert_eq!(broad_results.len(), 16);
        // Mixed: (t∈{0,1} ∧ s=0) ∪ c=2 → 4 + (18-12) - 2 = 4+6-2 = 8
        //   early_time ∩ sensor_zero: t∈{0,1}, s=0, c∈{0,1,2} → 2×1×3 = 6
        //   high_temp: t∈{0,1,2}, s∈{0,1}, c=2 → 3×2×1 = 6
        //   overlap: t∈{0,1}, s=0, c=2 → 2
        //   union: 6+6-2 = 10
        // Wait, let me recalculate.
        // early_time ∩ sensor_zero: t∈{0,1}, s=0, ANY c → 2×1×3 = 6
        // high_temp: ANY t, ANY s, c=2 → 3×2×1 = 6
        // Overlap: t∈{0,1}, s=0, c=2 → 2×1×1 = 2
        // mixed = 6 + 6 - 2 = 10
        assert_eq!(mixed_results.len(), 10);

        println!("    axes: time∈[0..2], sensor∈[0..1], temp∈[0..2]  (18 segments)");
        println!(
            "    early_time ∧ sensor₀ ∧ high_temp → {} segments → sums: {:?}",
            narrow_results.len(),
            narrow_results
        );
        println!(
            "    early_time ∨ sensor₀ ∨ high_temp → {} segments",
            broad_results.len()
        );
        println!(
            "    (early_time ∧ sensor₀) ∨ high_temp → {} segments → sums: {:?}",
            mixed_results.len(),
            mixed_results
        );
        println!("    → Heterogeneous axes carry independent semantics.");
        println!("    → Field composition changes inquiry without changing the space.");
    }
}
