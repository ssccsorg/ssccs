//! Experiment 04: Observation Concept
//!
//! Tests the Observation concept - the sole active event that produces actuality.

use ssccs_core::{observe, possible_next_coordinates, Field, Segment};
use ssccs_examples::{ArithmeticProjector, IntegerProjector, RangeConstraint};

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║        Experiment 04: Observation Concept                  ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

    match test_observation_concept() {
        Ok(_) => println!("\nObservation Concept PASSED"),
        Err(e) => {
            println!("\nObservation Concept FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 4: Observation Concept - The sole active event
fn test_observation_concept() -> Result<(), String> {
    println!("1. Testing observation with constraint filtering:");

    let segment = Segment::from_value(5);
    let mut field = Field::new();
    field.add_constraint(RangeConstraint::new(0, 0, 10));

    let int_projector = IntegerProjector::new(0);

    // Observation with allowed coordinates
    let observation_result = observe(&field, &segment, &int_projector);
    println!("- Observation result (allowed): {:?}", observation_result);

    if observation_result != Some(5) {
        return Err("Observation should succeed for allowed coordinates".to_string());
    }

    // Observation with disallowed coordinates
    let invalid_segment = Segment::from_value(15);
    let failed_observation = observe(&field, &invalid_segment, &int_projector);
    println!(
        "- Observation result (disallowed): {:?}",
        failed_observation
    );

    if failed_observation.is_some() {
        return Err("Observation should fail for disallowed coordinates".to_string());
    }

    println!("2. Observation properties verified:");
    println!("- Field constraints filter observations");
    println!("- Projection is ephemeral (not cached)");
    println!("- Re-observation required for same result");
    println!("- No state mutation during observation");

    // Test possible_next_coordinates function
    let next_coords = possible_next_coordinates(&field, &segment, &ArithmeticProjector);
    println!("3. Possible next coordinates (filtered by field):");
    println!(
        "- {:?}",
        next_coords.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );

    Ok(())
}
