//! Experiment: Transition Matrix
//!
//! Tests the Transition Matrix - relational topology as weighted directed graph.

use ssccs_core::{Coordinates, Field, segment_id_from_coords};
fn main() {
    println!("Experiment: Transition Matrix                    ");

    match test_transition_matrix() {
        Ok(_) => println!("\nTransition Matrix PASSED"),
        Err(e) => {
            println!("\nTransition Matrix FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 9: Transition Matrix - Relational topology
fn test_transition_matrix() -> Result<(), String> {
    println!("1. Testing Transition Matrix:");

    let mut field = Field::new();

    let from = Coordinates::new(vec![0]);
    let to1 = Coordinates::new(vec![1]);
    let to2 = Coordinates::new(vec![2]);

    field.add_transition(from.clone(), to1.clone(), 0.8);
    field.add_transition(from.clone(), to2.clone(), 0.2);

    let targets = field.transition_targets(&from);
    println!(
        "- From {:?} transition targets: {}",
        from.raw,
        targets.len()
    );

    for target in &targets {
        println!("- {:?}", target.as_bytes());
    }

    if targets.len() != 2 {
        return Err(format!("Expected 2 targets, got {}", targets.len()));
    }

    // Verify targets exist (weights are internal to Field)
    if !targets.contains(&segment_id_from_coords(&to1)) {
        return Err("Target to1 should be in transition targets".to_string());
    }
    if !targets.contains(&segment_id_from_coords(&to2)) {
        return Err("Target to2 should be in transition targets".to_string());
    }

    println!("2. Transition matrix verified:");
    println!("Weighted directed graph structure");
    println!("Multiple transitions from single source");
    println!("Target retrieval working (weights managed internally)");

    Ok(())
}
