//! SSCCS Proof of Concept - Constitutional Test 10: Integrated Workflow
//!
//! This test demonstrates the complete SSCCS pipeline from structure to observation.

use ssccs_core::{Coordinates, Field, Projector};
use ssccs_examples::CoordinateSumProjector;
use ssccs_schemes::Tensor3DTemplate;

/// Integrated workflow test - demonstrates complete SSCCS pipeline
fn test_integrated_workflow() -> Result<(), String> {
    println!("Integrated Workflow with 3D Tensor Scheme");

    // 1. Create a 3D tensor scheme (2x2x2)
    let scheme = Tensor3DTemplate::new(2, 2, 2).build();
    println!(
        "1. Created 3D tensor scheme (2x2x2) with {} segments",
        scheme.segments().count()
    );

    // 2. Create a field with a simple transition
    let mut field = Field::new();
    // Add a transition from (0,0,0) to (1,0,0) with weight 0.5
    let from_coords = Coordinates::new(vec![0, 0, 0]);
    let to_coords = Coordinates::new(vec![1, 0, 0]);
    field.add_transition(from_coords.clone(), to_coords.clone(), 0.5);
    println!("2. Created field with transition");

    // 3. Create a projector that sums coordinates
    let projector = CoordinateSumProjector;
    println!("3. Created CoordinateSumProjector");

    // 4. Perform observation on segment (0,0,0)
    let segment = scheme
        .segments()
        .find(|seg| seg.coordinates().raw == vec![0, 0, 0])
        .expect("Segment (0,0,0) should exist");
    let observation = projector.project(&field, segment);
    println!(
        "4. Observation result for segment (0,0,0): {:?}",
        observation
    );

    // 5. Validate adjacency relationships
    let neighbors = scheme.structural_neighbors(segment.id(), None);
    println!(
        "5. Structural neighbors of (0,0,0): {} neighbor(s)",
        neighbors.len()
    );
    for (neighbor_id, relation) in neighbors {
        let neighbor = scheme
            .segments()
            .find(|seg| seg.id() == &neighbor_id)
            .unwrap();
        println!(
            "- {:?} with relation {:?}",
            neighbor.coordinates().raw,
            relation
        );
    }

    // 6. Verify that the scheme has correct dimensionality
    assert_eq!(scheme.dimensionality(), 3);
    println!("6. Scheme dimensionality verified: 3");

    println!("Integrated workflow test passed");
    Ok(())
}

fn main() {
    println!("\n=== Constitutional Concept Test 10: Integrated Workflow ===\n");

    let test_func = test_integrated_workflow;
    match test_func() {
        Ok(()) => println!("\nAll tests passed!"),
        Err(e) => {
            eprintln!("\nTest failed: {}", e);
            std::process::exit(1);
        }
    }
}
