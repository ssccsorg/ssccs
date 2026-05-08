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
//! - **Union (∪)**: Broadens inquiry — admissible if either Field allows.
//! - **Intersection (∩)**: Narrows focus — admissible only if both allow.
//! - **Product (×)**: Parallel independent investigation — each Field governs
//!   a disjoint axis partition.

use ssccs_core::{Field, Segment, SpaceCoordinates};
use ssccs_examples::{CoordinateSumProjector, EvenConstraint, RangeConstraint};
use ssccs_field_synthesis::{IdentityField, compose_observe, intersection, product, union};

fn main() {
    println!("=== Field Synthesis: Composition Algebra ===\n");

    let tests: Vec<(&str, fn())> = vec![
        ("1. Identity Elements", test_identity),
        ("2. Commutativity", test_commutativity),
        ("3. Associativity", test_associativity),
        ("4. Absorption", test_absorption),
        ("5. Distributivity", test_distributivity),
        ("6. Product Semantics", test_product),
        ("7. Nested Composition", test_nested),
        ("8. Admissibility", test_admissibility),
        ("9. Expression Description", test_description),
        ("10. Transition Composition", test_transition),
        ("11. Idempotence", test_idempotence),
        ("12. compose_observe Bridge", test_compose_observe),
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
                if let Some(m) = e.downcast_ref::<&str>() {
                    println!("    Reason: {}", m);
                } else if let Some(m) = e.downcast_ref::<String>() {
                    println!("    Reason: {}", m);
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

fn coord(x: i64, y: i64, z: i64) -> SpaceCoordinates {
    SpaceCoordinates::new(vec![x, y, z])
}
fn coord_1d(x: i64) -> SpaceCoordinates {
    SpaceCoordinates::new(vec![x])
}

fn field_a() -> Field {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(0, 0, 10));
    f.add_constraint(EvenConstraint::new(0));
    f
}

fn field_b() -> Field {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(1, 0, 5));
    f
}

fn field_c() -> Field {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(2, 0, 3));
    f
}

// ==================== TESTS ====================

fn test_identity() {
    let u = union(field_a(), IdentityField::Empty);
    assert!(u.allows(&coord(2, 1, 0)));
    assert!(!u.allows(&coord(3, 1, 0)));

    let i = intersection(field_a(), IdentityField::Universal);
    assert!(i.allows(&coord(2, 1, 0)));
    assert!(!i.allows(&coord(3, 1, 0)));

    assert!(!union(IdentityField::Empty, IdentityField::Empty).allows(&coord(0, 0, 0)));
    assert!(
        intersection(IdentityField::Universal, IdentityField::Universal)
            .allows(&coord(999, -1, 100))
    );
}

fn test_commutativity() {
    let tests = [
        coord(2, 1, 0),
        coord(2, 10, 0),
        coord(3, 1, 0),
        coord(3, 10, 0),
        coord(4, 3, 5),
    ];
    let ab = union(field_a(), field_b());
    let ba = union(field_b(), field_a());
    for c in &tests {
        assert_eq!(ab.allows(c), ba.allows(c));
    }

    let ab = intersection(field_a(), field_b());
    let ba = intersection(field_b(), field_a());
    for c in &tests {
        assert_eq!(ab.allows(c), ba.allows(c));
    }
}

fn test_associativity() {
    let a = field_a();
    let b = field_b();
    let c = field_c();
    let tests = [
        coord(2, 1, 1),
        coord(3, 1, 1),
        coord(2, 10, 1),
        coord(2, 1, 5),
        coord(3, 10, 5),
        coord(4, 2, 2),
    ];
    let l = union(union(a.clone(), b.clone()), c.clone());
    let r = union(a.clone(), union(b.clone(), c.clone()));
    for t in &tests {
        assert_eq!(l.allows(t), r.allows(t));
    }

    let l = intersection(intersection(a.clone(), b.clone()), c.clone());
    let r = intersection(a.clone(), intersection(b.clone(), c.clone()));
    for t in &tests {
        assert_eq!(l.allows(t), r.allows(t));
    }
}

fn test_absorption() {
    let a = field_a();
    let b = field_b();
    let tests = [
        coord(2, 1, 0),
        coord(2, 10, 0),
        coord(3, 1, 0),
        coord(3, 10, 0),
    ];

    let la = union(a.clone(), intersection(a.clone(), b.clone()));
    for t in &tests {
        assert_eq!(la.allows(t), a.allows(t));
    }

    let la = intersection(a.clone(), union(a, b));
    let a2 = field_a();
    for t in &tests {
        assert_eq!(la.allows(t), a2.allows(t));
    }
}

fn test_distributivity() {
    let a = field_a();
    let b = field_b();
    let c = field_c();
    let tests = [
        coord(2, 1, 1),
        coord(3, 1, 1),
        coord(2, 10, 1),
        coord(2, 1, 5),
        coord(2, 10, 5),
        coord(4, 2, 2),
    ];
    let lhs = intersection(a.clone(), union(b.clone(), c.clone()));
    let rhs = union(
        intersection(a.clone(), b.clone()),
        intersection(a.clone(), c.clone()),
    );
    for t in &tests {
        assert_eq!(lhs.allows(t), rhs.allows(t));
    }
}

fn test_product() {
    let mut fa = Field::new();
    fa.add_constraint(RangeConstraint::new(0, 0, 10));
    fa.add_constraint(EvenConstraint::new(0));

    let pa = product(fa.clone(), IdentityField::Unit, 1);
    assert!(pa.allows(&coord_1d(2)));
    assert!(!pa.allows(&coord_1d(3)));
    assert!(!pa.allows(&coord_1d(12)));
}

fn test_nested() {
    let a = field_a();
    let b = field_b();
    let c = field_c();
    let n = intersection(union(a.clone(), b.clone()), c.clone());
    assert!(n.allows(&coord(2, 1, 2)));
    assert!(n.allows(&coord(2, 10, 2)));
    assert!(!n.allows(&coord(3, 1, 5)));

    let t = intersection(intersection(a.clone(), b.clone()), c.clone());
    assert!(t.allows(&coord(2, 1, 2)));
    assert!(!t.allows(&coord(3, 1, 2)));
    assert!(!t.allows(&coord(2, 10, 2)));
    assert!(!t.allows(&coord(2, 1, 5)));
}

fn test_admissibility() {
    let a = field_a();
    let b = field_b();
    let c = field_c();
    let narrow = intersection(intersection(a.clone(), b.clone()), c.clone());
    let broad = union(union(a.clone(), b.clone()), c.clone());

    assert!(narrow.allows(&coord(2, 1, 2)));
    assert!(!narrow.allows(&coord(3, 10, 5)));
    assert!(!narrow.allows(&coord(2, 10, 5)));
    assert!(broad.allows(&coord(2, 10, 5)));

    println!("  Same coord (2,10,5): Narrow=false, Broad=true");
}

fn test_description() {
    let d = union(field_a(), field_b()).describe();
    assert!(d.contains('∪'));
    let nd = intersection(union(field_a(), field_b()), field_c()).describe();
    assert!(nd.contains('∪') && nd.contains('∩'));
    let id = union(IdentityField::Empty, field_a()).describe();
    assert!(id.contains('∅'));
    println!("  Expression: {}", d);
    println!("  Nested:     {}", nd);
    println!("  Identity:   {}", id);
}

fn test_transition() {
    let mut x = Field::new();
    x.add_transition(coord(0, 0, 0), coord(1, 0, 0), 1.0);
    x.add_transition(coord(0, 0, 0), coord(2, 0, 0), 0.5);

    let mut y = Field::new();
    y.add_transition(coord(0, 0, 0), coord(2, 0, 0), 0.8);
    y.add_transition(coord(0, 0, 0), coord(3, 0, 0), 1.0);

    let o = coord(0, 0, 0);

    let ut = union(x.clone(), y.clone()).transition_targets(&o);
    assert_eq!(ut.len(), 3);

    let it = intersection(x.clone(), y.clone()).transition_targets(&o);
    assert_eq!(it.len(), 1);
    assert!(it.contains(&coord(2, 0, 0)));

    println!(
        "  X ∪ Y: {:?}",
        ut.iter().map(|c| &c.raw).collect::<Vec<_>>()
    );
    println!(
        "  X ∩ Y: {:?}",
        it.iter().map(|c| &c.raw).collect::<Vec<_>>()
    );
}

fn test_idempotence() {
    let a = field_a();
    let tests = [coord(2, 1, 0), coord(3, 1, 0), coord(12, 1, 0)];
    for t in &tests {
        assert_eq!(union(a.clone(), a.clone()).allows(t), a.allows(t));
        assert_eq!(intersection(a.clone(), a.clone()).allows(t), a.allows(t));
    }
    assert!(!union(IdentityField::Empty, IdentityField::Empty).allows(&coord(0, 0, 0)));
    assert!(
        intersection(IdentityField::Universal, IdentityField::Universal).allows(&coord(999, 0, 0))
    );
}

fn test_compose_observe() {
    let narrow = intersection(intersection(field_a(), field_b()), field_c());
    let projector = CoordinateSumProjector;

    let seg = Segment::new(coord(2, 1, 2));
    let obs = compose_observe(&narrow, &projector, &seg);
    assert_eq!(obs, Some(5));

    let seg_bad = Segment::new(coord(3, 10, 5));
    assert!(compose_observe(&narrow, &projector, &seg_bad).is_none());

    let seg_partial = Segment::new(coord(2, 10, 5));
    assert!(compose_observe(&narrow, &projector, &seg_partial).is_none());

    println!(
        "    A∩B∩C at (2,1,2): {:?}",
        compose_observe(&narrow, &projector, &seg)
    );
    println!(
        "    A∩B∩C at (3,10,5): {:?}",
        compose_observe(&narrow, &projector, &seg_bad)
    );
    println!(
        "    A∩B∩C at (2,10,5): {:?}",
        compose_observe(&narrow, &projector, &seg_partial)
    );
    println!("  → Observation through composed Fields is structurally real.");
}
