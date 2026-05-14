//! Field Synthesis Experiment: Field Composition Algebra
//!
//! Validates that Fields can be composed through union, intersection, and product
//! operations, and that these compositions satisfy expected algebraic properties.
//!
//! ## Structure
//!
//! - Algebraic laws (tests 1–12): commutativity, associativity, distributivity, etc.
//! - `Scenario` module: domain-specific scenarios demonstrating composition with
//!   heterogeneous axes — time, space, temperature, sensor identity, etc.
//!
//! Adding a scenario requires only implementing the `Scenario` trait and registering it.

use std::sync::Arc;

use ssccs_core::{Coordinates, Field, Segment, segment_id_from_coords};
use ssccs_examples::{CoordinateSumProjector, EvenConstraint, RangeConstraint};
use ssccs_field_synthesis::{IdentityField, compose_observe, intersection, product, union};

mod scenarios;

fn main() {
    println!("=== Field Synthesis: Composition Algebra ===\n");

    let mut passed = 0u32;
    let mut failed = 0u32;

    // ── algebraic laws ──
    let laws: Vec<(&str, fn())> = vec![
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

    for (name, test_fn) in &laws {
        print!("  {} ... ", name);
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(test_fn));
        let (ok, msg) = unwind_result(result);
        if ok {
            println!("PASSED");
            passed += 1;
        } else {
            println!("FAILED");
            if let Some(m) = msg {
                println!("    Reason: {}", m);
            }
            failed += 1;
        }
    }

    // ── scenarios ──
    for s in scenarios::registry() {
        print!("  Scenario: {} ... ", s.name());
        let result = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| s.run()));
        let (ok, msg) = unwind_result(result);
        if ok {
            println!("PASSED");
            passed += 1;
        } else {
            println!("FAILED");
            if let Some(m) = msg {
                println!("    Reason: {}", m);
            }
            failed += 1;
        }
    }

    let total = laws.len() + scenarios::registry().len();
    println!(
        "\nResults: {} passed, {} failed out of {} tests",
        passed, failed, total
    );
    if failed > 0 {
        std::process::exit(1);
    }
}

fn unwind_result(result: Result<(), Box<dyn std::any::Any + Send>>) -> (bool, Option<String>) {
    match result {
        Ok(()) => (true, None),
        Err(e) => {
            let msg = e
                .downcast_ref::<&str>()
                .map(|s| s.to_string())
                .or_else(|| e.downcast_ref::<String>().cloned());
            (false, msg)
        }
    }
}

// ==================== HELPERS ====================

fn coord(x: i64, y: i64, z: i64) -> Coordinates {
    Coordinates::new(vec![x, y, z])
}
fn coord_1d(x: i64) -> Coordinates {
    Coordinates::new(vec![x])
}

fn field_a() -> Arc<Field> {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(0, 0, 10));
    f.add_constraint(EvenConstraint::new(0));
    Arc::new(f)
}
fn field_b() -> Arc<Field> {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(1, 0, 5));
    Arc::new(f)
}
fn field_c() -> Arc<Field> {
    let mut f = Field::new();
    f.add_constraint(RangeConstraint::new(2, 0, 3));
    Arc::new(f)
}

// ==================== LAWS 1–12 ====================

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
    let l = union(union(Arc::clone(&a), Arc::clone(&b)), Arc::clone(&c));
    let r = union(Arc::clone(&a), union(Arc::clone(&b), Arc::clone(&c)));
    for t in &tests {
        assert_eq!(l.allows(t), r.allows(t));
    }
    let l = intersection(intersection(Arc::clone(&a), Arc::clone(&b)), Arc::clone(&c));
    let r = intersection(Arc::clone(&a), intersection(Arc::clone(&b), Arc::clone(&c)));
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
    let l = union(Arc::clone(&a), intersection(Arc::clone(&a), Arc::clone(&b)));
    for t in &tests {
        assert_eq!(l.allows(t), a.allows(t));
    }
    let l = intersection(Arc::clone(&a), union(Arc::clone(&a), Arc::clone(&b)));
    for t in &tests {
        assert_eq!(l.allows(t), a.allows(t));
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
    let lhs = intersection(Arc::clone(&a), union(Arc::clone(&b), Arc::clone(&c)));
    let rhs = union(
        intersection(Arc::clone(&a), Arc::clone(&b)),
        intersection(Arc::clone(&a), Arc::clone(&c)),
    );
    for t in &tests {
        assert_eq!(lhs.allows(t), rhs.allows(t));
    }
}

fn test_product() {
    let mut fa = Field::new();
    fa.add_constraint(RangeConstraint::new(0, 0, 10));
    fa.add_constraint(EvenConstraint::new(0));
    let fa = Arc::new(fa);
    let pa = product(fa.clone(), IdentityField::Unit, 1);
    assert!(pa.allows(&coord_1d(2)));
    assert!(!pa.allows(&coord_1d(3)));
    assert!(!pa.allows(&coord_1d(12)));
}

fn test_nested() {
    let a = field_a();
    let b = field_b();
    let c = field_c();
    let n = intersection(union(Arc::clone(&a), Arc::clone(&b)), Arc::clone(&c));
    assert!(n.allows(&coord(2, 1, 2)));
    assert!(n.allows(&coord(2, 10, 2)));
    assert!(!n.allows(&coord(3, 1, 5)));
    let t = intersection(intersection(Arc::clone(&a), Arc::clone(&b)), Arc::clone(&c));
    assert!(t.allows(&coord(2, 1, 2)));
    assert!(!t.allows(&coord(3, 1, 2)));
    assert!(!t.allows(&coord(2, 10, 2)));
    assert!(!t.allows(&coord(2, 1, 5)));
}

fn test_admissibility() {
    let a = field_a();
    let b = field_b();
    let c = field_c();
    let narrow = intersection(intersection(Arc::clone(&a), Arc::clone(&b)), Arc::clone(&c));
    let broad = union(union(Arc::clone(&a), Arc::clone(&b)), Arc::clone(&c));
    assert!(narrow.allows(&coord(2, 1, 2)));
    assert!(!narrow.allows(&coord(3, 10, 5)));
    assert!(!narrow.allows(&coord(2, 10, 5)));
    assert!(broad.allows(&coord(2, 10, 5)));
    println!("  Same coord (2,10,5): Narrow=false, Broad=true");
}

fn test_description() {
    let d = union(field_a(), field_b()).describe();
    assert!(d.contains('\u{222A}'));
    let nd = intersection(union(field_a(), field_b()), field_c()).describe();
    assert!(nd.contains('\u{222A}') && nd.contains('\u{2229}'));
    let id = union(IdentityField::Empty, field_a()).describe();
    assert!(id.contains('\u{2205}'));
    println!("  Expression: {}", d);
    println!("  Nested:     {}", nd);
    println!("  Identity:   {}", id);
}

fn test_transition() {
    let mut x_field = Field::new();
    x_field.add_transition(coord(0, 0, 0), coord(1, 0, 0), 1.0);
    x_field.add_transition(coord(0, 0, 0), coord(2, 0, 0), 0.5);
    let x = Arc::new(x_field);
    let mut y_field = Field::new();
    y_field.add_transition(coord(0, 0, 0), coord(2, 0, 0), 0.8);
    y_field.add_transition(coord(0, 0, 0), coord(3, 0, 0), 1.0);
    let y = Arc::new(y_field);
    let o = coord(0, 0, 0);
    let ut = union(x.clone(), y.clone());
    assert_eq!(ut.transition_targets(&o).len(), 3);
    let it = intersection(x.clone(), y.clone()).transition_targets(&o);
    assert_eq!(it.len(), 1);
    assert!(it.contains(&segment_id_from_coords(&coord(2, 0, 0))));
    println!(
        "  X\u{222A}Y: {:?}",
        ut.transition_targets(&o)
            .iter()
            .map(|id| id.as_bytes())
            .collect::<Vec<_>>()
    );
    println!(
        "  X\u{2229}Y: {:?}",
        it.iter().map(|id| id.as_bytes()).collect::<Vec<_>>()
    );
}

fn test_idempotence() {
    let a = field_a();
    for t in &[coord(2, 1, 0), coord(3, 1, 0), coord(12, 1, 0)] {
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
    assert_eq!(compose_observe(&narrow, &projector, &seg), Some(5));
    assert!(compose_observe(&narrow, &projector, &Segment::new(coord(3, 10, 5))).is_none());
    assert!(compose_observe(&narrow, &projector, &Segment::new(coord(2, 10, 5))).is_none());
    println!("  A\u{2229}B\u{2229}C at (2,1,2): Some(5)");
    println!("  A\u{2229}B\u{2229}C at (3,10,5): None");
    println!("  \u{2192} Observation through composed Fields is structurally real.");
}
