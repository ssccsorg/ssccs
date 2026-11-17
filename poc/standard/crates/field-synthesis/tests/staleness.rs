//! Composite staleness against the whitepaper's appendix (`sec-appendix-dynamic-field-evolution`).
//!
//! A composite holds a structure built at one version, and a constituent update makes that structure stale without
//! touching it. The count of rebuilds is what says the laziness is real rather than intended, so every case below
//! asserts it.

use std::sync::{Arc, Mutex};

use ssccs_core::{
    ConstraintSpec, ConstraintUpdate, Coordinates, EvenConstraint, EvolutionRule, EvolvingField,
    Field, FieldLogEntry, FieldTrigger, GtConstraint, RangeConstraint,
};
use ssccs_field_synthesis::{CompositionOp, LazyComposite, composite_version};

fn at(value: i64) -> Coordinates {
    Coordinates::new(vec![value])
}

fn event(time: i64, id: &str) -> FieldLogEntry {
    FieldLogEntry::Event {
        at: time,
        id: id.to_string(),
    }
}

fn shared(field: EvolvingField) -> Arc<Mutex<EvolvingField>> {
    Arc::new(Mutex::new(field))
}

#[test]
fn a_composite_version_follows_its_parts_and_the_operation() {
    let baseline = composite_version(CompositionOp::Union, &[0, 0]);

    assert_eq!(baseline, composite_version(CompositionOp::Union, &[0, 0]));
    assert_ne!(baseline, composite_version(CompositionOp::Union, &[0, 1]));
    assert_ne!(
        composite_version(CompositionOp::Union, &[1, 0]),
        composite_version(CompositionOp::Union, &[0, 1]),
        "position carries the constituent"
    );
    assert_ne!(
        baseline,
        composite_version(CompositionOp::Intersection, &[0, 0])
    );
    assert_ne!(
        baseline,
        composite_version(CompositionOp::Union, &[0, 0, 0])
    );
}

#[test]
fn the_structure_is_rebuilt_only_when_the_version_moved() {
    let mut admitted = Field::new();
    admitted.add_constraint(GtConstraint::new(0, 10));
    let left = shared(EvolvingField::new(admitted, 0, 0));
    left.lock()
        .expect("the field is not shared with a panicking holder")
        .add_rule(EvolutionRule::new(
            FieldTrigger::OnEvent {
                id: "open".to_string(),
            },
            ConstraintUpdate::Set(Vec::new()),
        ));

    let mut narrow = Field::new();
    narrow.add_constraint(RangeConstraint::new(0, 0, 100));
    let right = shared(EvolvingField::new(narrow, 0, 0));

    let mut composite = LazyComposite::new(CompositionOp::Union, left.clone(), right.clone());

    assert_eq!(composite.rebuilds(), 0, "composing is not a rebuild");
    assert!(composite.is_current());

    assert!(composite.allows(&at(5)), "the right side admits five");
    assert_eq!(composite.rebuilds(), 0, "nothing moved");

    left.lock()
        .expect("the field is not shared with a panicking holder")
        .record(event(1, "open"));

    assert!(!composite.is_current(), "the constituent moved");
    assert!(composite.allows(&at(5)));
    assert_eq!(composite.rebuilds(), 1, "the observation rebuilt it");

    assert!(composite.allows(&at(5)));
    assert_eq!(composite.rebuilds(), 1, "and only once");
}

#[test]
fn an_intersection_answers_the_new_set_after_the_update() {
    let mut wide = Field::new();
    wide.add_constraint(RangeConstraint::new(0, 0, 10));
    let left = shared(EvolvingField::new(wide, 0, 0));
    left.lock()
        .expect("the field is not shared with a panicking holder")
        .add_rule(EvolutionRule::new(
            FieldTrigger::OnEvent {
                id: "shrink".to_string(),
            },
            ConstraintUpdate::Set(vec![ConstraintSpec::Range { min: 0, max: 5 }]),
        ));

    let mut even = Field::new();
    even.add_constraint(EvenConstraint::new(0));
    let right = shared(EvolvingField::new(even, 0, 0));

    let mut composite =
        LazyComposite::new(CompositionOp::Intersection, left.clone(), right.clone());

    assert!(composite.allows(&at(8)), "even and inside the wide range");
    assert!(!composite.allows(&at(9)));

    left.lock()
        .expect("the field is not shared with a panicking holder")
        .record(event(1, "shrink"));

    assert!(!composite.allows(&at(8)), "eight left the narrowed range");
    assert!(composite.allows(&at(4)));
    assert_eq!(composite.rebuilds(), 1);
}

#[test]
fn a_product_reads_each_side_on_its_own_axes() {
    let mut first = Field::new();
    first.add_constraint(RangeConstraint::new(0, 0, 5));
    let left = shared(EvolvingField::new(first, 0, 0));

    // A product re-bases each side, so the right constituent is stated on its own axis zero and the partition puts
    // it on axis one of the product.
    let mut second = Field::new();
    second.add_constraint(GtConstraint::new(0, 0));
    let right = shared(EvolvingField::new(second, 0, 0));

    let mut composite = LazyComposite::new(CompositionOp::Product, left, right).with_left_axes(1);

    assert_eq!(composite.rebuilds(), 0);
    assert!(composite.allows(&Coordinates::new(vec![3, 7])));
    assert!(
        !composite.allows(&Coordinates::new(vec![7, 7])),
        "axis zero is out of range"
    );
    assert!(
        !composite.allows(&Coordinates::new(vec![3, 0])),
        "axis one must be above zero"
    );
}
