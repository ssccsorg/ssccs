use std::sync::Arc;

use ssccs_core::{Coordinates, Field, Projector, Segment};
use ssccs_examples::{CoordinateSumProjector, EvenConstraint, RangeConstraint};
use ssccs_field_synthesis::{compose_observe, intersection, union};

/// A self-contained demonstration that Field composition changes what is observable.
pub trait Scenario {
    fn name(&self) -> &'static str;
    fn run(&self);
}

/// All registered scenarios.
pub fn registry() -> Vec<Box<dyn Scenario>> {
    vec![
        Box::new(Grid2D {}),
        Box::new(SensorTimeTemp {}),
        Box::new(ComposePipeline {}),
        Box::new(ProductParallel {}),
        Box::new(IntersectMux {}),
        Box::new(ComposeVsUnion {}),
        Box::new(HardwareMappingFromSynthesis {}),
        Box::new(DynamicConstraints {}),
    ]
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

// ==================== OPERATOR-LEVEL COMPOSITION SCENARIOS ====================
//
// These scenarios demonstrate operator-level Field composition:
//   Compose (pipeline)  = projector A output → projector B input
//   Product (parallel)  = two projectors evaluate independently
//   Intersect (MUX)     = condition selects which projector to apply
//
// This is distinct from constraint-level composition (Union/Intersection/Product)
// above. Constraint composition asks "does this coordinate satisfy constraints?"
// Operator composition asks "what does this projector output feed into another?"
//
// Proven by nex-calc (F x I x H -> F') and backported into SSCCS core.

struct ComposePipeline;

impl Scenario for ComposePipeline {
    fn name(&self) -> &'static str {
        "Operator Pipeline: seq(proj_a, proj_b)"
    }

    fn run(&self) {
        use ssccs_examples::IntegerProjector;

        let seg = Segment::new(Coordinates::new(vec![5, 3]));
        let proj_a = IntegerProjector::new(0); // extracts axis 0 → 5
        let proj_b = IntegerProjector::new(0); // extracts axis 0 from new seg

        let intermediate = proj_a.project(&Field::new(), &seg).unwrap();
        let pipe_seg = Segment::new(Coordinates::new(vec![intermediate, 7]));
        let result = proj_b.project(&Field::new(), &pipe_seg).unwrap();

        assert_eq!(intermediate, 5, "pipeline step 1: extract axis0 → 5");
        assert_eq!(
            result, 5,
            "pipeline step 2: pipe 5 into new segment, extract → 5"
        );
        println!("    seq(extract0, extract0) on [5,3] → pipe → {}", result);
        println!("    → Compose = pipeline: Projector A output wired to Projector B input");
    }
}

struct ProductParallel;

impl Scenario for ProductParallel {
    fn name(&self) -> &'static str {
        "Operator Product: par(proj_a, proj_b)"
    }

    fn run(&self) {
        use ssccs_examples::IntegerProjector;

        let seg = Segment::new(Coordinates::new(vec![10, 42]));
        let pa = IntegerProjector::new(0);
        let pb = IntegerProjector::new(1);

        let r1 = pa.project(&Field::new(), &seg).unwrap();
        let r2 = pb.project(&Field::new(), &seg).unwrap();

        assert_eq!(r1, 10, "product A: extract axis 0 from [10,42]");
        assert_eq!(r2, 42, "product B: extract axis 1 from [10,42]");
        println!("    par(extract0, extract1) on [10,42] → ({}, {})", r1, r2);
        println!("    → Product = parallel: independent projectors, no data flow");
    }
}

struct IntersectMux;

impl Scenario for IntersectMux {
    fn name(&self) -> &'static str {
        "Operator Intersect: mux(cond, proj_then, proj_else)"
    }

    fn run(&self) {
        use ssccs_examples::IntegerProjector;

        let then_proj = IntegerProjector::new(0);
        let else_proj = IntegerProjector::new(1);

        // cond: axis0 > 5
        let seg = Segment::new(Coordinates::new(vec![8, 3]));
        let result = match seg.coordinates().get_axis(0).unwrap() > 5 {
            true => then_proj.project(&Field::new(), &seg).unwrap(),
            false => else_proj.project(&Field::new(), &seg).unwrap(),
        };
        assert_eq!(result, 8, "axis0=8 > 5 → then → extract0 = 8");

        let seg2 = Segment::new(Coordinates::new(vec![2, 99]));
        let result2 = match seg2.coordinates().get_axis(0).unwrap() > 5 {
            true => then_proj.project(&Field::new(), &seg2).unwrap(),
            false => else_proj.project(&Field::new(), &seg2).unwrap(),
        };
        assert_eq!(result2, 99, "axis0=2 ≤ 5 → else → extract1 = 99");

        println!("    mux(axis0>5, extract0, extract1) on [8,3] → {}", result);
        println!(
            "    mux(axis0>5, extract0, extract1) on [2,99] → {}",
            result2
        );
        println!("    → Intersect = MUX: comparator selects active projector path");
    }
}

struct ComposeVsUnion;

impl Scenario for ComposeVsUnion {
    fn name(&self) -> &'static str {
        "Compose ≠ Constraint Union"
    }

    fn run(&self) {
        use ssccs_examples::{EvenConstraint, RangeConstraint};

        // Constraint Union: admissible if A OR B allows
        let mut fa = Field::new();
        fa.add_constraint(EvenConstraint::new(0));
        fa.add_constraint(RangeConstraint::new(0, 0, 10));
        let mut fb = Field::new();
        fb.add_constraint(RangeConstraint::new(1, 0, 5));

        let coord = Coordinates::new(vec![3, 3]); // axis0=3 (odd → A rejects), axis1=3 (B accepts)
        assert!(!fa.allows(&coord), "A rejects odd axis0");
        assert!(fb.allows(&coord), "B accepts axis1=3");
        assert!(fa.allows(&coord) || fb.allows(&coord), "Union accepts");

        // Operator Compose: A must produce output BEFORE B can consume it
        use ssccs_examples::IntegerProjector;
        let step1 = IntegerProjector::new(0).project(&fa, &Segment::new(coord));
        // IntegerProjector ignores constraints — it always extracts
        assert_eq!(
            step1,
            Some(3),
            "Projector extracts regardless of constraint"
        );
        println!("    Constraint Union: A ∨ B at [3,3] → admissible (B accepts)");
        println!("    Operator Compose: extract0 → [3] → needs only Projector, not constraint");
        println!("    → Compose chains Projectors; Union filters by Field constraints");
        println!("    → Two distinct dimensions of Field composition");
    }
}

struct HardwareMappingFromSynthesis;

impl Scenario for HardwareMappingFromSynthesis {
    fn name(&self) -> &'static str {
        "Hardware Mapping: field-synthesis → hardware-mapping"
    }

    fn run(&self) {
        use ssccs_hardware_mapping::*;

        let pipe = compose_to_pipeline(2);
        assert!(matches!(
            pipe,
            HardwarePrimitive::Pipeline { stages: 2, .. }
        ));

        let par = product_to_parallel(2);
        assert!(matches!(par, HardwarePrimitive::Parallel { units: 2, .. }));

        let mux = intersect_to_mux("axis0>5", compose_to_pipeline(1), compose_to_pipeline(1));
        assert!(matches!(mux, HardwarePrimitive::Mux { .. }));

        let sv = generate_pipeline_sv(2, "proj_sum2d", "proj_mul");
        assert!(sv.contains("proj_sum2d"));
        assert!(sv.contains("proj_mul"));

        println!("    Compose (pipeline) → 2-stage pipeline: verified");
        println!("    Product (parallel) → dual DSP: verified");
        println!("    Intersect (MUX) → comparator + MUX: verified");
        println!("    SV generation for compose pipeline: verified");
        println!("    → field-synthesis drives hardware-mapping crate");
        println!("    → This closes the gap: constraint algebra → hardware primitives");
    }
}

// ── Register new scenarios in registry() ──
// This is appended to the existing registry() above.
// In practice, the registry function would be expanded to include these.

// ==================== DYNAMIC CONSTRAINT SCENARIO ====================
//
// Demonstrates nex-calc's Hint pattern: constraints can be added,
// removed, and cleared dynamically — changing the Field's admissibility
// without changing the Segments.

struct DynamicConstraints;

impl Scenario for DynamicConstraints {
    fn name(&self) -> &'static str {
        "Dynamic Constraints: add / remove / clear"
    }

    fn run(&self) {
        use ssccs_examples::{EvenConstraint, RangeConstraint};

        let mut field = Field::new();
        let seg = Segment::new(Coordinates::new(vec![5, 0]));

        // Initially no constraints — everything admissible
        assert!(field.allows(seg.coordinates()));
        assert_eq!(field.num_constraints(), 0);
        println!("    Field with no constraints: admissible");

        // Add constraint: axis 0 must be even
        field.add_constraint(EvenConstraint::new(0));
        assert!(!field.allows(seg.coordinates())); // 5 is odd
        assert_eq!(field.num_constraints(), 1);
        println!(
            "    Added EvenConstraint([0]): admissible={}",
            field.allows(seg.coordinates())
        );

        // Add another constraint: axis 0 in [0, 10]
        field.add_constraint(RangeConstraint::new(0, 0, 10));
        assert!(!field.allows(seg.coordinates())); // still odd
        assert_eq!(field.num_constraints(), 2);
        println!(
            "    Added RangeConstraint(0, 0, 10): constraints={}",
            field.num_constraints()
        );

        // Remove the even constraint at index 0
        assert!(field.remove_constraint(0));
        assert!(field.allows(seg.coordinates())); // now only range, 5 in [0,10]
        assert_eq!(field.num_constraints(), 1);
        println!(
            "    Removed EvenConstraint: admissible={}",
            field.allows(seg.coordinates())
        );

        // Clear all constraints
        field.clear_constraints();
        assert!(field.allows(seg.coordinates())); // back to fully admissible
        assert_eq!(field.num_constraints(), 0);
        println!(
            "    Cleared all constraints: admissible={}",
            field.allows(seg.coordinates())
        );

        // Dynamic constraint equivalent to nex-calc's `constrain` / `clear` commands
        println!("    → Dynamic constraints mirror nex-calc's Hint lifecycle");
        println!("    → constrain gt 10 → add_constraint(GreaterThan(10))");
        println!("    → constrain clear  → clear_constraints()");
    }
}

// ── Update registry() — already appended to in the previous block.
// The registry() function now includes all operator + dynamic scenarios.
// Please also add "DynamicConstraints" to the vec in registry() above.
