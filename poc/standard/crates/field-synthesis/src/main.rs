//! Field Synthesis Experiment: Field Composition Algebra
//!
//! Validates that Fields can be composed through union, intersection, and product
//! operations, and that these compositions satisfy expected algebraic properties.
//!
//! ## Background
//!
//! The SSCCS philosophy establishes that "the manner in which we combine questions
//! becomes a form of epistemology":
//!
//! - **Union (∪)**: Broaden the inquiry — combine Fields so that a coordinate is
//!   admissible if either Field allows it.
//! - **Intersection (∩)**: Narrow the focus — a coordinate is admissible only if
//!   both Fields allow it.
//! - **Product (×)**: Independent parallel investigation — each Field constrains
//!   the same coordinate space independently, and all must agree.
//!
//! This experiment validates that these operations behave as a proper algebra:
//! commutativity, associativity, identity elements, absorption, and distributivity,
//! then demonstrates composition with actual constraints to show that the composed
//! Field changes what is admissible.

use ssccs_core::{Field, SpaceCoordinates};
use ssccs_examples::{EvenConstraint, RangeConstraint};
use ssccs_field_synthesis::{ComposedField, CompositionOp, IdentityField, intersection, union};

fn main() {
    println!("=== Field Synthesis: Composition Algebra ===\n");

    let tests: Vec<(&str, fn())> = vec![
        ("1. Identity Elements", test_identity_elements),
        ("2. Commutativity", test_commutativity),
        ("3. Associativity", test_associativity),
        ("4. Absorption", test_absorption),
        ("5. Distributivity", test_distributivity),
        ("6. Product Semantics", test_product_semantics),
        ("7. Nested Composition", test_nested_composition),
        (
            "8. Composition Changes Admissibility",
            test_admissibility_composition,
        ),
        ("9. Expression Description", test_expression_description),
        ("10. Transition Composition", test_transition_composition),
    ];

    let mut passed = 0u32;
    let mut failed = 0u32;

    for (name, test_fn) in &tests {
        print!("  {} ... ", name);
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(test_fn));
        match result {
            Ok(()) => {
                println!("PASSED");
                passed += 1;
            }
            Err(e) => {
                println!("FAILED");
                if let Some(msg) = e.downcast_ref::<&str>() {
                    println!("    Reason: {}", msg);
                } else if let Some(msg) = e.downcast_ref::<String>() {
                    println!("    Reason: {}", msg);
                }
                failed += 1;
            }
        }
    }

    println!(
        "\nResults: {} passed, {} failed out of {} tests",
        passed,
        failed,
        tests.len()
    );
    if failed > 0 {
        std::process::exit(1);
    }
}

// ==================== TEST FIELD CONSTRUCTORS ====================

fn build_field_a() -> Field {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(0, 0, 10));
    f.add_constraint(EvenConstraint::new(0));
    f
}

fn build_field_b() -> Field {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(1, 0, 5));
    f
}

fn build_field_c() -> Field {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(2, 0, 3));
    f
}

// ==================== COORDINATE HELPERS ====================

fn coord(x: i64, y: i64, z: i64) -> SpaceCoordinates {
    SpaceCoordinates::new(vec![x, y, z])
}

// ==================== TEST 1: IDENTITY ELEMENTS ====================

fn test_identity_elements() {
    // Union identity: A ∪ ∅ = A
    let union_with_empty = union(build_field_a(), IdentityField::Empty);
    assert!(
        union_with_empty.allows(&coord(2, 1, 0)),
        "Union with empty should allow what A allows"
    );
    assert!(
        !union_with_empty.allows(&coord(3, 1, 0)),
        "Union with empty should reject what A rejects"
    );
    assert!(
        !union_with_empty.allows(&coord(12, 1, 0)),
        "Union with empty should reject out-of-range for A"
    );

    // Intersection identity: A ∩ ⊤ = A
    let inter_with_universal = intersection(build_field_a(), IdentityField::Universal);
    assert!(
        inter_with_universal.allows(&coord(2, 1, 0)),
        "Intersection with universal should allow what A allows"
    );
    assert!(
        !inter_with_universal.allows(&coord(3, 1, 0)),
        "Intersection with universal should reject what A rejects"
    );

    // Empty union empty = empty
    let empty_empty = union(IdentityField::Empty, IdentityField::Empty);
    assert!(
        !empty_empty.allows(&coord(0, 0, 0)),
        "Empty ∪ Empty should reject all coordinates"
    );

    // Universal intersected with universal = universal
    let uni_uni = intersection(IdentityField::Universal, IdentityField::Universal);
    assert!(
        uni_uni.allows(&coord(999, -1, 100)),
        "Universal ∩ Universal should allow everything"
    );
}

// ==================== TEST 2: COMMUTATIVITY ====================

fn test_commutativity() {
    let a_union_b = union(build_field_a(), build_field_b());
    let b_union_a = union(build_field_b(), build_field_a());

    let test_coords = vec![
        coord(2, 1, 0),
        coord(2, 10, 0),
        coord(3, 1, 0),
        coord(3, 10, 0),
        coord(4, 3, 5),
    ];

    for c in &test_coords {
        assert_eq!(
            a_union_b.allows(c),
            b_union_a.allows(c),
            "Union commutativity violated at {:?}",
            c.raw
        );
    }

    let a_inter_b = intersection(build_field_a(), build_field_b());
    let b_inter_a = intersection(build_field_b(), build_field_a());

    for c in &test_coords {
        assert_eq!(
            a_inter_b.allows(c),
            b_inter_a.allows(c),
            "Intersection commutativity violated at {:?}",
            c.raw
        );
    }
}

// ==================== TEST 3: ASSOCIATIVITY ====================

fn test_associativity() {
    let fa = build_field_a();
    let fb = build_field_b();
    let fc = build_field_c();

    // Union: (A ∪ B) ∪ C = A ∪ (B ∪ C)
    let left_union = union(union(fa.clone(), fb.clone()), fc.clone());
    let right_union = union(fa.clone(), union(fb.clone(), fc.clone()));

    let test_coords = vec![
        coord(2, 1, 1),
        coord(3, 1, 1),
        coord(2, 10, 1),
        coord(2, 1, 5),
        coord(3, 10, 5),
        coord(4, 2, 2),
    ];

    for c in &test_coords {
        assert_eq!(
            left_union.allows(c),
            right_union.allows(c),
            "Union associativity violated at {:?}",
            c.raw
        );
    }

    // Intersection: (A ∩ B) ∩ C = A ∩ (B ∩ C)
    let left_inter = intersection(intersection(fa.clone(), fb.clone()), fc.clone());
    let right_inter = intersection(fa.clone(), intersection(fb.clone(), fc.clone()));

    for c in &test_coords {
        assert_eq!(
            left_inter.allows(c),
            right_inter.allows(c),
            "Intersection associativity violated at {:?}",
            c.raw
        );
    }
}

// ==================== TEST 4: ABSORPTION ====================

fn test_absorption() {
    let fa = build_field_a();
    let fb = build_field_b();

    let a_union_a_inter_b = union(fa.clone(), intersection(fa.clone(), fb.clone()));
    let test_coords = vec![
        coord(2, 1, 0),
        coord(2, 10, 0),
        coord(3, 1, 0),
        coord(3, 10, 0),
    ];

    for c in &test_coords {
        assert_eq!(
            a_union_a_inter_b.allows(c),
            fa.allows(c),
            "Absorption law 1 violated at {:?}: A ∪ (A ∩ B) should equal A",
            c.raw
        );
    }

    let a_inter_a_union_b = intersection(fa.clone(), union(fa, fb));
    let fa2 = build_field_a();

    for c in &test_coords {
        assert_eq!(
            a_inter_a_union_b.allows(c),
            fa2.allows(c),
            "Absorption law 2 violated at {:?}: A ∩ (A ∪ B) should equal A",
            c.raw
        );
    }
}

// ==================== TEST 5: DISTRIBUTIVITY ====================

fn test_distributivity() {
    let fa = build_field_a();
    let fb = build_field_b();
    let fc = build_field_c();

    let a_inter_b_union_c = intersection(fa.clone(), union(fb.clone(), fc.clone()));
    let a_inter_b_union_a_inter_c = union(
        intersection(fa.clone(), fb.clone()),
        intersection(fa.clone(), fc.clone()),
    );

    let test_coords = vec![
        coord(2, 1, 1),
        coord(3, 1, 1),
        coord(2, 10, 1),
        coord(2, 1, 5),
        coord(2, 10, 5),
        coord(4, 2, 2),
    ];

    for c in &test_coords {
        assert_eq!(
            a_inter_b_union_c.allows(c),
            a_inter_b_union_a_inter_c.allows(c),
            "Distributivity violated at {:?}: A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C)",
            c.raw
        );
    }
}

// ==================== TEST 6: PRODUCT SEMANTICS ====================

fn test_product_semantics() {
    // Product: both Fields check the same coordinate space independently.
    let prod = ComposedField::new(build_field_a(), build_field_b(), CompositionOp::Product);

    // Field A: axis[0] even and in [0,10]; Field B: axis[1] in [0,5]
    let coord_valid = coord(2, 3, 0);
    let coord_a_rejects = coord(3, 3, 0);
    let coord_b_rejects = coord(2, 10, 0);

    assert!(
        prod.allows(&coord_valid),
        "Product should allow valid coordinate"
    );
    assert!(
        !prod.allows(&coord_a_rejects),
        "Product should reject when A rejects"
    );
    assert!(
        !prod.allows(&coord_b_rejects),
        "Product should reject when B rejects"
    );

    // Product is commutative: A × B = B × A
    let prod_ba = ComposedField::new(build_field_b(), build_field_a(), CompositionOp::Product);
    for c in &[
        coord(2, 3, 0),
        coord(3, 3, 0),
        coord(2, 10, 0),
        coord(11, 6, 0),
    ] {
        assert_eq!(
            prod.allows(c),
            prod_ba.allows(c),
            "Product commutativity violated at {:?}",
            c.raw
        );
    }

    // Identity: A × ⊤ = A
    let prod_with_universal = ComposedField::new(
        build_field_a(),
        IdentityField::Universal,
        CompositionOp::Product,
    );
    assert_eq!(
        prod_with_universal.allows(&coord(2, 1, 0)),
        build_field_a().allows(&coord(2, 1, 0)),
        "A × ⊤ should equal A"
    );
    assert_eq!(
        prod_with_universal.allows(&coord(3, 1, 0)),
        build_field_a().allows(&coord(3, 1, 0)),
        "A × ⊤ should equal A"
    );
}

// ==================== TEST 7: NESTED COMPOSITION ====================

fn test_nested_composition() {
    let fa = build_field_a();
    let fb = build_field_b();
    let fc = build_field_c();

    // (A ∪ B) ∩ C
    let nested = intersection(union(fa.clone(), fb.clone()), fc.clone());

    assert!(
        nested.allows(&coord(2, 1, 2)),
        "Nested (A∪B)∩C should allow (2,1,2)"
    );
    assert!(
        nested.allows(&coord(2, 10, 2)),
        "Nested (A∪B)∩C should allow (2,10,2) because A∪B allows it"
    );
    assert!(
        !nested.allows(&coord(3, 1, 5)),
        "Nested (A∪B)∩C should reject (3,1,5) because C rejects"
    );

    // ((A ∩ B) ∩ C) = A ∩ B ∩ C
    let triple_inter = intersection(intersection(fa.clone(), fb.clone()), fc.clone());
    assert!(
        triple_inter.allows(&coord(2, 1, 2)),
        "Triple intersection should allow (2,1,2)"
    );
    assert!(
        !triple_inter.allows(&coord(3, 1, 2)),
        "Triple intersection should reject (3,1,2) because A rejects"
    );
    assert!(
        !triple_inter.allows(&coord(2, 10, 2)),
        "Triple intersection should reject (2,10,2) because B rejects"
    );
    assert!(
        !triple_inter.allows(&coord(2, 1, 5)),
        "Triple intersection should reject (2,1,5) because C rejects"
    );
}

// ==================== TEST 8: COMPOSITION CHANGES ADMISSIBILITY ====================

fn test_admissibility_composition() {
    let fa = build_field_a();
    let fb = build_field_b();
    let fc = build_field_c();

    // Narrow inquiry: where ALL three constraints hold
    let narrow = intersection(intersection(fa.clone(), fb.clone()), fc.clone());

    // Broad inquiry: where ANY constraint holds
    let broad = union(union(fa.clone(), fb.clone()), fc.clone());

    let coord_valid = coord(2, 1, 2);
    assert!(narrow.allows(&coord_valid), "Narrow should allow (2,1,2)");
    assert!(broad.allows(&coord_valid), "Broad should allow (2,1,2)");

    let coord_all_violate = coord(3, 10, 5);
    assert!(
        !narrow.allows(&coord_all_violate),
        "Narrow should reject (3,10,5)"
    );
    assert!(
        !broad.allows(&coord_all_violate),
        "Broad should reject (3,10,5)"
    );

    let coord_only_a = coord(2, 10, 5);
    assert!(
        !narrow.allows(&coord_only_a),
        "Narrow should reject (2,10,5)"
    );
    assert!(
        broad.allows(&coord_only_a),
        "Broad should allow (2,10,5) — A allows"
    );

    let coord_only_b = coord(3, 3, 5);
    assert!(
        !narrow.allows(&coord_only_b),
        "Narrow should reject (3,3,5)"
    );
    assert!(
        broad.allows(&coord_only_b),
        "Broad should allow (3,3,5) — B allows"
    );

    println!(
        "  Same coord (2,10,5): Narrow={}, Broad={}",
        narrow.allows(&coord_only_a),
        broad.allows(&coord_only_a)
    );
    println!(
        "  Same coord (3,3,5):  Narrow={}, Broad={}",
        narrow.allows(&coord_only_b),
        broad.allows(&coord_only_b)
    );
    println!("  → Different compositions of the same Fields produce");
    println!("    different admissibility from the same coordinate space.");
}

// ==================== TEST 9: EXPRESSION DESCRIPTION ====================

fn test_expression_description() {
    let composed = union(build_field_a(), build_field_b());
    let desc = composed.describe();
    assert!(desc.contains('\u{222A}'), "Should contain union symbol");
    println!("  Expression: {}", desc);

    let nested = intersection(union(build_field_a(), build_field_b()), build_field_c());
    let nested_desc = nested.describe();
    assert!(
        nested_desc.contains('\u{222A}') && nested_desc.contains('\u{2229}'),
        "Should contain both operators"
    );
    println!("  Nested:     {}", nested_desc);

    let with_id = union(IdentityField::Empty, build_field_a());
    let id_desc = with_id.describe();
    assert!(id_desc.contains('\u{2205}'), "Should contain empty symbol");
    println!("  Identity:   {}", id_desc);
}

// ==================== TEST 10: TRANSITION COMPOSITION ====================

fn test_transition_composition() {
    // Build fields with transitions for composition testing
    let mut field_x = Field::new();
    field_x.add_transition(coord(0, 0, 0), coord(1, 0, 0), 1.0);
    field_x.add_transition(coord(0, 0, 0), coord(2, 0, 0), 0.5);

    let mut field_y = Field::new();
    field_y.add_transition(coord(0, 0, 0), coord(2, 0, 0), 0.8);
    field_y.add_transition(coord(0, 0, 0), coord(3, 0, 0), 1.0);

    let origin = coord(0, 0, 0);

    // Union: (X ∪ Y) at (0,0,0) → targets from both: [(1,0,0), (2,0,0), (3,0,0)]
    let union_xy = union(field_x.clone(), field_y.clone());
    let union_targets = union_xy.transition_targets(&origin);
    assert!(
        union_targets.contains(&coord(1, 0, 0)),
        "Union should include (1,0,0) from X"
    );
    assert!(
        union_targets.contains(&coord(2, 0, 0)),
        "Union should include (2,0,0) from both"
    );
    assert!(
        union_targets.contains(&coord(3, 0, 0)),
        "Union should include (3,0,0) from Y"
    );
    assert_eq!(union_targets.len(), 3, "Union should have 3 unique targets");

    // Intersection: (X ∩ Y) at (0,0,0) → targets common to both: [(2,0,0)]
    let inter_xy = intersection(field_x.clone(), field_y.clone());
    let inter_targets = inter_xy.transition_targets(&origin);
    assert!(
        inter_targets.contains(&coord(2, 0, 0)),
        "Intersection should include (2,0,0) common to both"
    );
    assert_eq!(inter_targets.len(), 1, "Intersection should have 1 target");

    // Product (no split): (X × Y) at (0,0,0) → targets common to both: [(2,0,0)]
    let prod_xy = ComposedField::new(field_x.clone(), field_y.clone(), CompositionOp::Product);
    let prod_targets = prod_xy.transition_targets(&origin);
    assert!(
        prod_targets.contains(&coord(2, 0, 0)),
        "Product (no split) should include (2,0,0) common to both"
    );
    assert_eq!(prod_targets.len(), 1, "Product (no split) should have 1 target");

    // Identity: ∅ has no transitions
    let union_with_empty = union(field_x.clone(), IdentityField::Empty);
    let empty_targets = union_with_empty.transition_targets(&origin);
    assert_eq!(
        empty_targets.len(),
        2,
        "Union with empty should retain all targets from X"
    );
    assert!(empty_targets.contains(&coord(1, 0, 0)));
    assert!(empty_targets.contains(&coord(2, 0, 0)));

    println!("  X ∪ Y targets: {:?}", union_targets.iter().map(|c| &c.raw).collect::<Vec<_>>());
    println!("  X ∩ Y targets: {:?}", inter_targets.iter().map(|c| &c.raw).collect::<Vec<_>>());
    println!("  X × Y targets: {:?}", prod_targets.iter().map(|c| &c.raw).collect::<Vec<_>>());
    println!("  → Transition topology is preserved through Field composition.");
}
