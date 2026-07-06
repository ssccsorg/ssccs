//! Experiment: ComposeField — Operator-Level Field Composition
//!
//! Tests operator-level Field composition distinct from constraint-level
//! Union/Intersection/Product in field-synthesis.
//!
//! Constraint composition asks: "Does this coordinate satisfy Field A AND/OR B?"
//! Operator composition asks: "What does Field A's projector output, fed through
//! Field B's projector, produce?"
//!
//! Hardware mapping:
//!   Compose (seq)  = Pipeline (A output wired to B input)
//!   Product (par)  = Parallel DSP (A and B evaluate independently)
//!   Intersect (cond)= MUX + Comparator (if C then A else B)
//!
//! Proven by nex-calc (nexus PR #143): F x I x H -> F' on 23 operators.

use ssccs_core::{Coordinates, Field, Projector, Segment};
use ssccs_examples::IntegerProjector;

fn main() {
    println!("Experiment: ComposeField — Operator-Level Composition\n");

    let mut failed = false;
    if test_compose_pipeline().is_err() { failed = true; }
    if test_product_parallel().is_err() { failed = true; }
    if test_intersect_mux().is_err() { failed = true; }
    if test_compose_vs_constraint_union().is_err() { failed = true; }
    if test_hardware_mapping_patterns().is_err() { failed = true; }

    if failed {
        println!("\nComposeField: FAILED");
        std::process::exit(1);
    }
    println!("\nComposeField: PASSED");
}

// ── Test 1: Compose = Pipeline ───────────────────────────────────

/// compose(extract_axis_0, extract_axis_1):
/// Step 1: Projector A reads axis 0 from segment → value X
/// Step 2: Create new segment from X → Projector B reads its axis 0
/// This IS the pipeline: A's output is B's input.
fn test_compose_pipeline() -> Result<(), String> {
    println!("1. Compose (Pipeline)");

    // Segment A: coord [5, 3] → Projector A reads axis 0 → 5
    let seg_a = Segment::new(Coordinates::new(vec![5, 3]));
    let proj_a = IntegerProjector::new(0);

    let intermediate = proj_a.project(&Field::new(), &seg_a)
        .ok_or("Step 1 failed")?;
    println!("  Step 1: extract axis 0 from [5,3] = {}", intermediate);
    assert_eq!(intermediate, 5);

    // Step 2: create a segment from intermediate, pipe through Projector B
    // Projector B reads axis 0 from a new segment [5, 7] → 5
    let seg_b = Segment::new(Coordinates::new(vec![intermediate, 7]));
    let proj_b = IntegerProjector::new(0);
    let final_result = proj_b.project(&Field::new(), &seg_b)
        .ok_or("Step 2 failed")?;

    println!("  Step 2: pipe result into new segment [{}], extract = {}", intermediate, final_result);
    assert_eq!(final_result, 5);
    println!("  Hardware: Projector A output → wire → Segment B → Projector B");
    Ok(())
}

// ── Test 2: Product = Parallel ───────────────────────────────────

/// product(extract_axis_0, extract_axis_1):
/// Both projectors evaluate independently on the same segment.
/// No data flows between them.
fn test_product_parallel() -> Result<(), String> {
    println!("\n2. Product (Parallel)");

    let seg = Segment::new(Coordinates::new(vec![10, 42]));
    let pa = IntegerProjector::new(0);
    let pb = IntegerProjector::new(1);

    let r1 = pa.project(&Field::new(), &seg).ok_or("A failed")?;
    let r2 = pb.project(&Field::new(), &seg).ok_or("B failed")?;

    println!("  product(axis0, axis1) on [10,42] = ({}, {})", r1, r2);
    assert_eq!(r1, 10);
    assert_eq!(r2, 42);
    println!("  Hardware: Projector-A ∥ Projector-B (independent, zero coordination)");
    Ok(())
}

// ── Test 3: Intersect = MUX ───────────────────────────────────────

/// intersect(axis0>5, axis0, axis1):
/// If axis 0 > 5, project axis 0. Otherwise, project axis 1.
fn test_intersect_mux() -> Result<(), String> {
    println!("\n3. Intersect (MUX)");

    let seg = Segment::new(Coordinates::new(vec![8, 3]));
    let then_proj = IntegerProjector::new(0);
    let else_proj = IntegerProjector::new(1);

    let result = match seg.coordinates().get_axis(0).unwrap_or(0) > 5 {
        true => then_proj.project(&Field::new(), &seg).ok_or("then failed")?,
        false => else_proj.project(&Field::new(), &seg).ok_or("else failed")?,
    };
    println!("  intersect(axis0>5, extract0, extract1) at [8,3]: {}", result);
    assert_eq!(result, 8, "axis0=8 > 5 → use then (extract0) → 8");

    let seg2 = Segment::new(Coordinates::new(vec![2, 99]));
    let result2 = match seg2.coordinates().get_axis(0).unwrap_or(0) > 5 {
        true => then_proj.project(&Field::new(), &seg2).ok_or("then failed")?,
        false => else_proj.project(&Field::new(), &seg2).ok_or("else failed")?,
    };
    println!("  intersect(axis0>5, extract0, extract1) at [2,99]: {}", result2);
    assert_eq!(result2, 99, "axis0=2 ≤ 5 → use else (extract1) → 99");
    println!("  Hardware: Comparator[axis0>5] → MUX[extract0 | extract1]");
    Ok(())
}

// ── Test 4: Compose ≠ Constraint Union ──────────────────────────

/// Operator Compose requires sequential dataflow.
/// Constraint Union checks independently — no ordering.
fn test_compose_vs_constraint_union() -> Result<(), String> {
    println!("\n4. Compose ≠ Constraint Union");

    let mut fa = Field::new();
    fa.add_constraint(ssccs_examples::EvenConstraint::new(0));
    fa.add_constraint(ssccs_examples::RangeConstraint::new(0, 0, 10));

    let mut fb = Field::new();
    fb.add_constraint(ssccs_examples::RangeConstraint::new(1, 0, 5));

    // [3,3]: axis0=3 (odd, composes fails step1), axis1=3 (ok for B)
    let coord = Coordinates::new(vec![3, 3]);
    let allowed_by_a = fa.allows(&coord);
    let allowed_by_b = fb.allows(&coord);

    println!("  [3,3]: A allows={}, B allows={}", allowed_by_a, allowed_by_b);
    println!("  Union (A ∨ B) accepts: {}", allowed_by_a || allowed_by_b);
    println!("  Compose needs A first (dataflow): cannot proceed");

    let proj_a = IntegerProjector::new(0);
    // Compose step 1: extract axis 0 — this works even if A's constraints fail
    // because IntegerProjector ignores constraints
    let step1 = proj_a.project(&Field::new(), &Segment::new(coord.clone()));
    assert_eq!(step1, Some(3));
    println!("  Projector extracts value regardless of constraint admissibility");
    println!("  Key insight: the Projector evaluates; the Field gates.");
    println!("  Compose chains Projectors; Union combines Field constraints.");
    Ok(())
}

// ── Test 5: Hardware Mapping via ssccs-hardware-mapping ──────────

fn test_hardware_mapping_patterns() -> Result<(), String> {
    println!("\n5. Hardware Mapping Patterns");

    let pipeline = ssccs_hardware_mapping::compose_to_pipeline(2);
    let parallel = ssccs_hardware_mapping::product_to_parallel(2);
    let mux = ssccs_hardware_mapping::intersect_to_mux("axis0>5",
        ssccs_hardware_mapping::compose_to_pipeline(1),
        ssccs_hardware_mapping::compose_to_pipeline(1),
    );

    assert!(matches!(pipeline, ssccs_hardware_mapping::HardwarePrimitive::Pipeline { stages: 2, .. }));
    assert!(matches!(parallel, ssccs_hardware_mapping::HardwarePrimitive::Parallel { units: 2, .. }));
    assert!(matches!(mux, ssccs_hardware_mapping::HardwarePrimitive::Mux { .. }));

    let sv = ssccs_hardware_mapping::generate_pipeline_sv(2, "add", "mul");
    assert!(sv.contains("compose_pipeline"));

    println!("  Compose → Pipeline (2-stage): verified + SV generated");
    println!("  Product → Parallel DSP: verified");
    println!("  Intersect → MUX: verified");
    println!("\n  Ref: nex-calc proved F x I x H -> F' with 23 operators.");
    println!("  This crate bridges operator-level composition to SSCCS core.");
    Ok(())
}
