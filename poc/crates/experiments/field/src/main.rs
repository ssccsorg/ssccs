//! Experiment 02: Field Concept
//!
//! Tests the Field concept - mutable constraint substrate and transition topology.

use ssccs_core::{Field, SpaceCoordinates};
use ssccs_examples::{EvenConstraint, RangeConstraint};

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║        Experiment 02: Field Concept                        ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

    match test_field_concept() {
        Ok(_) => println!("\nField Concept PASSED"),
        Err(e) => {
            println!("\nField Concept FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 2: Field Concept - Mutable constraint substrate
fn test_field_concept() -> Result<(), String> {
    let mut field = Field::new();

    // 1. Constraint addition
    field.add_constraint(RangeConstraint::new(0, 0, 10));
    field.add_constraint(RangeConstraint::new(1, 0, 5));
    field.add_constraint(EvenConstraint::new(0));

    println!("1. Field constraints added:");
    println!("- {}", field.describe_constraints());

    // 2. Constraint validation
    let valid_coords = SpaceCoordinates::new(vec![4, 3, 100]); // Even, within ranges
    let invalid_range = SpaceCoordinates::new(vec![15, 3, 0]);
    let invalid_even = SpaceCoordinates::new(vec![3, 2, 0]);

    println!("2. Constraint validation:");
    println!(
        "- Valid coords [4, 3, 100]: {}",
        field.allows(&valid_coords)
    );
    println!(
        "- Invalid range [15, 3, 0]: {}",
        field.allows(&invalid_range)
    );
    println!("- Invalid even [3, 2, 0]: {}", field.allows(&invalid_even));

    if !field.allows(&valid_coords) {
        return Err("Valid coordinates should be allowed".to_string());
    }
    if field.allows(&invalid_range) {
        return Err("Coordinates out of range should be rejected".to_string());
    }
    if field.allows(&invalid_even) {
        return Err("Odd coordinates should be rejected by EvenConstraint".to_string());
    }
    println!("All constraint validations passed");

    // 3. Transition rules (relational topology)
    let from_coords = SpaceCoordinates::new(vec![1, 2, 3]);
    let to_coords = SpaceCoordinates::new(vec![2, 2, 3]);
    field.add_transition(from_coords.clone(), to_coords.clone(), 1.0);

    println!("3. Transition rules added:");
    println!("- From [1, 2, 3] → [2, 2, 3] with weight 1.0");

    let transitions = field.transition_targets(&from_coords);
    println!(
        "- Transition targets: {:?}",
        transitions
            .iter()
            .map(|c| c.raw.clone())
            .collect::<Vec<_>>()
    );

    if transitions.len() != 1 || transitions[0] != to_coords {
        return Err("Transition should return the correct target coordinates".to_string());
    }

    // 4. Field mutability demonstration
    println!("4. Field mutability demonstrated:");
    println!("- Constraints can be added after creation");
    println!("- Transition rules can be added dynamically");
    println!("- Field does not own Segments (separation of concerns)");

    Ok(())
}
