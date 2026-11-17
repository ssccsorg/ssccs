//! Field evolution against the whitepaper's appendix (`sec-appendix-dynamic-field-evolution`).
//!
//! Every case drives the log by hand, because the log is the whole input to an evolution. The times and the entries
//! in these tests are the record, so a change in what a trigger means shows up as a different set of fired rules
//! rather than as a different number of iterations.

use ssccs_core::{
    ConstraintSpec, ConstraintUpdate, Coordinates, EvolutionRule, EvolvingField, Field,
    FieldLogEntry, FieldTrigger, GtConstraint,
};

fn at(value: i64) -> Coordinates {
    Coordinates::new(vec![value])
}

fn event(time: i64, id: &str) -> FieldLogEntry {
    FieldLogEntry::Event {
        at: time,
        id: id.to_string(),
    }
}

fn tick(time: i64) -> FieldLogEntry {
    event(time, "tick")
}

/// The appendix's `temperature_alarm`: `value > 30`, widened to 50 after ten seconds, then to 60 when suppression
/// is activated.
#[test]
fn the_appendix_temperature_alarm() {
    let mut field = Field::new();
    field.add_constraint(GtConstraint::new(0, 30));

    let mut alarm = EvolvingField::new(field, 0, 0);
    alarm.add_rule(EvolutionRule::new(
        FieldTrigger::After { delta: 10 },
        ConstraintUpdate::Set(vec![ConstraintSpec::Gt { value: 50 }]),
    ));
    alarm.add_rule(EvolutionRule::new(
        FieldTrigger::OnEvent {
            id: "suppression_activated".to_string(),
        },
        ConstraintUpdate::Set(vec![ConstraintSpec::Gt { value: 60 }]),
    ));

    assert_eq!(alarm.version(), 0);
    assert!(alarm.allows(&at(31)));
    assert!(!alarm.allows(&at(30)), "the base constraint is strict");

    let quiet = alarm.record(tick(9));
    assert!(!quiet.fired_any(), "nine seconds is not ten");
    assert_eq!(alarm.version(), 0);

    let widened = alarm.record(tick(10));
    assert_eq!(widened.fired, vec![0]);
    assert_eq!(alarm.version(), 1);
    assert!(alarm.allows(&at(55)));
    assert!(!alarm.allows(&at(45)));

    let early = alarm.record(tick(19));
    assert!(
        !early.fired_any(),
        "the clock is the last update, not the last entry"
    );

    let rewidened = alarm.record(tick(20));
    assert_eq!(rewidened.fired, vec![0]);
    assert_eq!(alarm.version(), 2);

    let suppressed = alarm.record(event(21, "suppression_activated"));
    assert_eq!(suppressed.fired, vec![1]);
    assert_eq!(alarm.version(), 3);
    assert!(alarm.allows(&at(61)));
    assert!(!alarm.allows(&at(60)));

    assert!(
        !alarm.deterministic(),
        "the suppression event originates outside the model"
    );
}

#[test]
fn an_update_restates_the_set_and_bumps_the_version() {
    let mut room = Field::new();
    room.add_constraint(GtConstraint::new(0, 10));

    let mut evolving = EvolvingField::new(room, 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::OnEvent {
            id: "open".to_string(),
        },
        ConstraintUpdate::Set(Vec::new()),
    ));

    assert!(!evolving.allows(&at(0)));

    let opened = evolving.record(event(1, "open"));
    assert_eq!(opened.version, 1);
    assert!(
        evolving.allows(&at(0)),
        "an empty set admits the whole space"
    );
}

#[test]
fn adding_keeps_what_the_field_carries() {
    let mut field = Field::new();
    field.add_constraint(GtConstraint::new(0, 0));

    let mut evolving = EvolvingField::new(field, 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::OnEvent {
            id: "cap".to_string(),
        },
        ConstraintUpdate::Add(vec![ConstraintSpec::Range { min: 0, max: 10 }]),
    ));

    assert!(evolving.allows(&at(40)));
    evolving.record(event(1, "cap"));
    assert!(evolving.allows(&at(10)));
    assert!(!evolving.allows(&at(11)));
    assert!(!evolving.allows(&at(0)), "the earlier constraint stays");
}

#[test]
fn the_projection_trigger_reads_the_observation() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::ProjectionAbove { threshold: 30 },
        ConstraintUpdate::Set(vec![ConstraintSpec::Gt { value: 50 }]),
    ));

    let cold = evolving.record(FieldLogEntry::Observed {
        at: 1,
        projection: 30,
    });
    assert!(!cold.fired_any(), "the threshold is strict");

    let hot = evolving.record(FieldLogEntry::Observed {
        at: 2,
        projection: 31,
    });
    assert_eq!(hot.fired, vec![0]);
    assert!(evolving.allows(&at(55)));
    assert!(!evolving.allows(&at(45)));
}

#[test]
fn the_dependency_trigger_fires_on_the_named_field() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::OnUpdateOf {
            field: "line_pressure".to_string(),
        },
        ConstraintUpdate::Set(vec![ConstraintSpec::Range { min: 0, max: 5 }]),
    ));

    let other = evolving.record(FieldLogEntry::Updated {
        at: 1,
        field: "temperature".to_string(),
        version: 4,
    });
    assert!(!other.fired_any());

    let wanted = evolving.record(FieldLogEntry::Updated {
        at: 2,
        field: "line_pressure".to_string(),
        version: 1,
    });
    assert_eq!(wanted.fired, vec![0]);
}

#[test]
fn all_fires_on_the_entry_that_completes_the_set() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::All(vec![
            FieldTrigger::OnEvent {
                id: "armed".to_string(),
            },
            FieldTrigger::OnEvent {
                id: "tripped".to_string(),
            },
        ]),
        ConstraintUpdate::Set(vec![ConstraintSpec::Range { min: 0, max: 1 }]),
    ));

    let armed = evolving.record(event(1, "armed"));
    assert!(!armed.fired_any(), "one of two is not both");

    let tripped = evolving.record(event(2, "tripped"));
    assert_eq!(tripped.fired, vec![0]);

    let later = evolving.record(event(3, "armed"));
    assert!(
        !later.fired_any(),
        "both have already happened, so the conjunction does not rise again"
    );
}

#[test]
fn any_fires_on_each_occurrence() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::Any(vec![
            FieldTrigger::OnEvent {
                id: "a".to_string(),
            },
            FieldTrigger::OnEvent {
                id: "b".to_string(),
            },
        ]),
        ConstraintUpdate::Add(vec![ConstraintSpec::Even]),
    ));

    assert_eq!(evolving.record(event(1, "a")).fired, vec![0]);
    assert_eq!(evolving.record(event(2, "b")).fired, vec![0]);
    assert!(!evolving.record(event(3, "c")).fired_any());
    assert_eq!(evolving.version(), 2);
}

#[test]
fn sequence_waits_for_each_part_in_order() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::Sequence(vec![
            FieldTrigger::OnEvent {
                id: "arm".to_string(),
            },
            FieldTrigger::OnEvent {
                id: "fire".to_string(),
            },
        ]),
        ConstraintUpdate::Set(vec![ConstraintSpec::Range { min: 0, max: 1 }]),
    ));

    assert!(
        !evolving.record(event(1, "fire")).fired_any(),
        "nothing armed it"
    );
    assert_eq!(evolving.record(event(2, "arm")).fired, Vec::<usize>::new());
    assert_eq!(evolving.record(event(3, "fire")).fired, vec![0]);
}

#[test]
fn determinism_is_a_property_of_the_triggers() {
    assert!(FieldTrigger::After { delta: 5 }.deterministic());
    assert!(FieldTrigger::ProjectionAbove { threshold: 0 }.deterministic());
    assert!(
        FieldTrigger::OnUpdateOf {
            field: "f".to_string()
        }
        .deterministic()
    );
    assert!(
        !FieldTrigger::OnEvent {
            id: "e".to_string()
        }
        .deterministic()
    );
    assert!(
        !FieldTrigger::Any(vec![
            FieldTrigger::After { delta: 5 },
            FieldTrigger::OnEvent {
                id: "e".to_string()
            },
        ])
        .deterministic()
    );
    assert!(
        FieldTrigger::All(vec![
            FieldTrigger::After { delta: 5 },
            FieldTrigger::OnUpdateOf {
                field: "f".to_string()
            },
        ])
        .deterministic()
    );
}

#[test]
fn one_entry_applies_each_rule_once() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::After { delta: 0 },
        ConstraintUpdate::Set(vec![ConstraintSpec::Even]),
    ));

    let first = evolving.record(FieldLogEntry::Created { at: 0 });
    assert_eq!(first.fired.len(), 1, "an immediate trigger fires");
    let second = evolving.record(tick(0));
    assert_eq!(
        second.fired.len(),
        1,
        "a rule fires once per entry, never in a loop"
    );
    assert_eq!(second.version, 2);
}

#[test]
fn the_log_keeps_the_updates_it_applied() {
    let mut evolving = EvolvingField::new(Field::new(), 0, 0);
    evolving.add_rule(EvolutionRule::new(
        FieldTrigger::After { delta: 1 },
        ConstraintUpdate::Set(vec![ConstraintSpec::Gt { value: 0 }]),
    ));

    evolving.record(tick(1));

    assert_eq!(
        evolving.log(),
        &[
            FieldLogEntry::Created { at: 0 },
            FieldLogEntry::Event {
                at: 1,
                id: "tick".to_string()
            },
            FieldLogEntry::Applied { at: 1, rule: 0 },
        ]
    );
}
