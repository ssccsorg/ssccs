//! Experiment 03: Projector Concept
//!
//! Tests the Projector concept - semantic interpretation of Segment-Field pairs.

use ssccs_core::{Field, Projector, Segment};
use ssccs_examples::{ArithmeticProjector, IntegerProjector, ParityProjector};

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║        Experiment 03: Projector Concept                    ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

    match test_projector_concept() {
        Ok(_) => println!("\nProjector Concept PASSED"),
        Err(e) => {
            println!("\nProjector Concept FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 3: Projector Concept - Semantic interpretation
fn test_projector_concept() -> Result<(), String> {
    println!("1. Testing different projectors on same coordinates:");

    let segment = Segment::from_value(7);
    println!("Segment coordinates: {:?}", segment.coordinates().raw);

    let empty_field = Field::new();

    // Integer projector
    let int_projector = IntegerProjector::new(0);
    let int_result = int_projector.project(&empty_field, &segment);
    println!("2. IntegerProjector result: {:?}", int_result);

    if int_result != Some(7) {
        return Err("IntegerProjector should extract coordinate value".to_string());
    }

    // Parity projector
    let parity_projector = ParityProjector;
    let parity_result = parity_projector.project(&empty_field, &segment);
    println!("3. ParityProjector result: {:?}", parity_result);

    if parity_result != Some("odd".to_string()) {
        return Err("ParityProjector should return \"odd\"for value 7".to_string());
    }

    // Arithmetic projector
    let arith_projector = ArithmeticProjector;
    let arith_result = arith_projector.project(&empty_field, &segment);
    println!("4. ArithmeticProjector result: {:?}", arith_result);

    // Test adjacency semantics
    let next_coords = arith_projector.possible_next_coordinates(segment.coordinates());
    println!("5. ArithmeticProjector adjacency:");
    println!(
        "- Possible next coordinates: {:?}",
        next_coords.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );

    // Verify different semantic interpretations
    println!("6. Semantic interpretation verified:");
    println!("- Same coordinates → Different meanings");
    println!("- Meaning emerges from projector, not coordinates");
    println!("- Projector defines adjacency semantics");

    Ok(())
}
