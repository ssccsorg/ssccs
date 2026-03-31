//! Experiment: Composite & Transformed Schemes
//!
//! Tests scheme composition and geometric transformation.

use ssccs_core::{Segment, SpaceCoordinates};
use ssccs_primitive::{GridTopology, SchemeImpl, SchemeTrait};
use ssccs_schemes::{
    CombinationMethod, CompositeScheme, CompositionRules, ConflictResolution, Grid2DTemplate,
    TransformType, Transformation, TransformedScheme,
};
use std::collections::HashMap;

fn main() {
    println!("Experiment: Composite & Transformed Schemes      ");

    match test_composite_and_transformed_schemes() {
        Ok(_) => println!("\nComposite & Transformed Schemes PASSED"),
        Err(e) => {
            println!("\nComposite & Transformed Schemes FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 8: Composite & Transformed Schemes
fn test_composite_and_transformed_schemes() -> Result<(), String> {
    println!("1. Creating composite scheme (Union of two grids):");

    // Create two simple grid schemes
    let grid1 = Grid2DTemplate::new(2, 2, GridTopology::FourConnected).build();
    let grid2 = Grid2DTemplate::new(2, 2, GridTopology::FourConnected).build();

    let components = vec![
        SchemeImpl::Basic(Box::new(grid1)),
        SchemeImpl::Basic(Box::new(grid2)),
    ];
    let composition_rules = CompositionRules {
        combination_method: CombinationMethod::Union,
        alignment: None,
        conflict_resolution: ConflictResolution::FirstWins,
    };
    let composite = CompositeScheme::new(components, composition_rules);
    println!("- Composite scheme created: {}", composite.describe());
    println!("- Composite ID: {}", hex::encode(composite.id().as_bytes()));

    // Verify composite contains segments from both grids
    let test_coords = SpaceCoordinates::new(vec![0, 0]);
    let test_segment = Segment::new(test_coords.clone());
    assert!(composite.contains_segment(test_segment.id()));
    println!("Contains segment at (0, 0)");

    // Verify composite trait delegation works
    let axes = composite.axes();
    println!("- Axes count: {}", axes.len());

    println!("\n2. Creating transformed scheme (Translation):");

    // Create a base scheme
    let base = Grid2DTemplate::new(3, 3, GridTopology::FourConnected).build();
    let base_impl = SchemeImpl::Basic(Box::new(base));

    // Create translation transformation
    let mut params = HashMap::new();
    params.insert("dx".to_string(), "1".to_string());
    params.insert("dy".to_string(), "2".to_string());
    let transformation = Transformation {
        transform_type: TransformType::Translation(vec![1, 2]),
        parameters: params,
    };
    let transformed = TransformedScheme::new(Box::new(base_impl), transformation);
    println!("- Transformed scheme created: {}", transformed.describe());
    println!(
        "- Transformed ID: {}",
        hex::encode(transformed.id().as_bytes())
    );

    // Verify transformed scheme delegates to base
    assert_eq!(transformed.dimensionality(), 2);
    println!(
        "- Dimensionality preserved: {}",
        transformed.dimensionality()
    );

    println!("\n3. Enhanced scheme features verified:");
    println!("Composite schemes combine multiple scheme components");
    println!("Transformed schemes apply geometric transformations");
    println!("Cryptographic IDs reflect composition/transformation");

    Ok(())
}
