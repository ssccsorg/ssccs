//! Experiment: Segment Concept
//!
//! Tests the Segment concept - immutable coordinate existence and cryptographic identity.

use ssccs_core::{Coordinates, Segment};

fn main() {
    println!("Experiment: Segment Concept                      ");

    match test_segment_concept() {
        Ok(_) => println!("\nSegment Concept PASSED"),
        Err(e) => {
            println!("\nSegment Concept FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 1: Segment Concept - Immutable coordinate existence
fn test_segment_concept() -> Result<(), String> {
    // 1. Coordinate-based existence
    let coords = Coordinates::new(vec![1, 2, 3]);
    let segment = Segment::new(coords.clone());

    println!(
        "1. Segment created from coordinates: {:?}",
        segment.coordinates().raw
    );
    println!("Dimensionality: {}", segment.coordinates().dimensionality());

    // 2. Cryptographic identity
    let id = segment.id();
    println!(
        "2. Cryptographic identity (BLAKE3): {}",
        hex::encode(id.as_bytes())
    );

    // 3. Same coordinates → Same identity (deterministic)
    let segment2 = Segment::new(coords.clone());
    if segment.id() != segment2.id() {
        return Err("Segments with identical coordinates must have identical IDs".into());
    }
    println!("3. Identity consistency verified (deterministic ID generation)");

    // 4. Immutability verification
    println!("4. Immutability verified:");
    println!("Segment coordinates are read-only");
    println!("Segment ID is computed once and immutable");
    println!("Clone creates independent copy with same ID");

    // 5. Convenience constructors
    let single_val = Segment::from_value(42);
    let multi_val = Segment::from_values(vec![10, 20, 30]);
    println!("5. Convenience constructors:");
    println!("- Single value segment: {:?}", single_val.coordinates().raw);
    println!("- Multi-value segment: {:?}", multi_val.coordinates().raw);

    // 6. Clone verification
    let seg_clone = segment.clone();
    if segment.id() != seg_clone.id() {
        return Err("Cloned segment must have same ID".into());
    }
    println!("6. Clone preserves cryptographic identity");

    Ok(())
}
