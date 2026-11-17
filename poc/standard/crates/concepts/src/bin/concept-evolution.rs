//! Experiment 12: Field Evolution
//!
//! A Field's admissible set changes because its log says so. The appendix's `temperature_alarm` drives the run:
//! `value > 30`, widened to 50 after ten seconds, then to 60 when suppression is activated.

use ssccs_core::{
    ConstraintSpec, ConstraintUpdate, Coordinates, EvolutionRule, EvolvingField, Field,
    FieldLogEntry, FieldTrigger, GtConstraint,
};

fn main() {
    println!("Experiment 12: Field Evolution");

    match run() {
        Ok(_) => println!("\nField Evolution PASSED"),
        Err(e) => {
            println!("\nField Evolution FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

fn at(value: i64) -> Coordinates {
    Coordinates::new(vec![value])
}

fn run() -> Result<(), String> {
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

    println!("1. The declared field:");
    println!("- {}", alarm.field().describe_constraints());
    println!(
        "- version {}, deterministic {}",
        alarm.version(),
        alarm.deterministic()
    );

    let log = [
        FieldLogEntry::Event {
            at: 9,
            id: "tick".to_string(),
        },
        FieldLogEntry::Event {
            at: 10,
            id: "tick".to_string(),
        },
        FieldLogEntry::Event {
            at: 19,
            id: "tick".to_string(),
        },
        FieldLogEntry::Event {
            at: 20,
            id: "tick".to_string(),
        },
        FieldLogEntry::Event {
            at: 21,
            id: "suppression_activated".to_string(),
        },
    ];

    println!("2. The log decides:");
    for entry in log {
        let time = entry.at();
        let report = alarm.record(entry);
        let fired = if report.fired.is_empty() {
            "nothing".to_string()
        } else {
            report
                .fired
                .iter()
                .map(|rule| rule.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        };
        println!(
            "- t={time:>2}: fired {fired} -> version {}, {}",
            report.version,
            alarm.field().describe_constraints()
        );
    }

    // 3. The result, checked rather than printed.
    if alarm.version() != 3 {
        return Err(format!("expected three updates, got {}", alarm.version()));
    }
    if alarm.allows(&at(61)) && !alarm.allows(&at(55)) {
        println!("3. Admissible now: value > 60");
    } else {
        return Err(format!(
            "the last update should admit 61 and refuse 55: {} and {}",
            alarm.allows(&at(61)),
            alarm.allows(&at(55))
        ));
    }

    if alarm.deterministic() {
        return Err("an external event makes this evolution non-deterministic".to_string());
    }
    println!("- deterministic: false, because suppression arrives from outside");

    Ok(())
}
