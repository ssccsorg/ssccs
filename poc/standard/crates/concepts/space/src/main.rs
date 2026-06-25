//! Experiment: Space Concept
//!
//! Tests the Space concept - structured coordinate spaces (BooleanSpace, IntegerSpace).

use ssccs_core::{Coordinates, Segment};
use ssccs_schemes::{BooleanSpace, IntegerSpace};

fn main() {
    println!("Experiment: Space Concept                        ");

    match test_space_concept() {
        Ok(_) => println!("\nSpace Concept PASSED"),
        Err(e) => {
            println!("\nSpace Concept FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 5: Space Concept - Structured coordinate spaces
fn test_space_concept() -> Result<(), String> {
    println!("1. BooleanSpace - Boolean values:");

    // Test true value
    let true_space = BooleanSpace::new(true);
    println!(
        "- Created from true: coordinates {:?}, value = {}",
        true_space.coordinates().raw,
        true_space.value()
    );
    println!("- ID: {}", hex::encode(true_space.id().as_bytes()));

    // Test false value
    let false_space = BooleanSpace::new(false);
    println!(
        "- Created from false: coordinates {:?}, value = {}",
        false_space.coordinates().raw,
        false_space.value()
    );
    println!("- ID: {}", hex::encode(false_space.id().as_bytes()));

    // Test deref to Segment
    let segment_ref: &Segment = &true_space;
    println!(
        "- Dereferences to Segment: {:?}",
        segment_ref.coordinates().raw
    );

    // Test From<bool> trait
    let from_bool: BooleanSpace = true.into();
    if !from_bool.value() {
        return Err("From<bool> true should create BooleanSpace with true value".to_string());
    }
    println!("From<bool> trait works");

    // Test From<Coordinates> trait
    let coords = Coordinates::new(vec![1]); // 1 = true
    let from_coords: BooleanSpace = coords.clone().into();
    if !from_coords.value() {
        return Err("From<Coordinates> [1] should create BooleanSpace with true value".to_string());
    }
    println!("From<Coordinates> trait works");

    println!("\n2. IntegerSpace - Single-axis convenience:");

    let int_space = IntegerSpace::new(42);
    println!("- Created from value: {:?}", int_space.coordinates().raw);
    println!("- ID: {}", hex::encode(int_space.id().as_bytes()));

    // Test conversions
    let _from_segment = IntegerSpace::from_segment(segment_ref.clone());
    println!("Converted from Segment");

    let _from_coords: IntegerSpace = coords.clone().into();
    println!("From<Coordinates> trait works");

    Ok(())
}
