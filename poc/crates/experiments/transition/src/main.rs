//! Experiment 09: Transition Matrix
//!
//! Tests the Transition Matrix - relational topology as weighted directed graph.

use ssccs_core::{Field, SpaceCoordinates};

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║        Experiment 09: Transition Matrix                    ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

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

    let from = SpaceCoordinates::new(vec![0]);
    let to1 = SpaceCoordinates::new(vec![1]);
    let to2 = SpaceCoordinates::new(vec![2]);

    field.add_transition(from.clone(), to1.clone(), 0.8);
    field.add_transition(from.clone(), to2.clone(), 0.2);

    let targets = field.transition_targets(&from);
    println!(
        "- From {:?} transition targets: {}",
        from.raw,
        targets.len()
    );

    for target in &targets {
        println!("- {:?}", target.raw);
    }

    if targets.len() != 2 {
        return Err(format!("Expected 2 targets, got {}", targets.len()));
    }

    // Verify targets exist (weights are internal to Field)
    if !targets.contains(&to1) {
        return Err("Target to1 should be in transition targets".to_string());
    }
    if !targets.contains(&to2) {
        return Err("Target to2 should be in transition targets".to_string());
    }

    println!("2. Transition matrix verified:");
    println!("- Weighted directed graph structure");
    println!("- Multiple transitions from single source");
    println!("- Target retrieval working (weights managed internally)");

    Ok(())
}
