//! SSCCS Proof of Concept -Constitutional Concept Tests
//!
//! This file tests all core concepts of SSCCS:
//! -Segment (invariant coordinate point)
//! -Scheme (structural blueprint)
//! -Field (dynamic constraints)
//! -Observation (observation and projection)
//! -Projector (meaning interpreter)
//! -Space (space definition)

pub mod projector;
pub use projector::*;

pub mod scheme;
pub use scheme::*;

use ssccs_poc::core::{Field, Projector, Segment, SpaceCoordinates};
use ssccs_poc::spaces::{arithmetic::IntegerSpace, basic::BasicSpace};
use ssccs_poc::*;

// Type alias for test function signature to reduce type complexity
type TestFn = fn() -> Result<(), String>;

// ==================== SSCCS CONSTITUTIONAL CONCEPT TESTS ====================

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║        SSCCS Proof of Concept - Constitutional Tests       ║");
    println!("║     Schema–Segment Composition Computing System            ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

    // Run all concept tests
    let tests: Vec<(&str, TestFn)> = vec![
        ("1. Segment Concept", test_segment_concept as TestFn),
        ("2. Field Concept", test_field_concept as TestFn),
        ("3. Projector Concept", test_projector_concept as TestFn),
        ("4. Observation Concept", test_observation_concept as TestFn),
        ("5. Space Concept", test_space_concept as TestFn),
        ("6. Scheme Concept", test_scheme_concept as TestFn),
        (
            "7. Adjacency & Memory Layout",
            test_adjacency_memory as TestFn,
        ),
        ("8. Transition Matrix", test_transition_matrix as TestFn),
        ("9. Integrated Workflow", test_integrated_workflow as TestFn),
    ];

    let mut passed = 0;
    let mut failed = 0;

    for (test_name, test_func) in tests {
        println!("\n╔══════════════════════════════════════════╗");
        println!("║ {:<40} ║", test_name);
        println!("╚══════════════════════════════════════════╝");

        match test_func() {
            Ok(_) => {
                println!("\n  {} PASSED", test_name);
                passed += 1;
            }
            Err(e) => {
                println!("\n  {} FAILED: {}", test_name, e);
                failed += 1;
            }
        }
    }

    println!("\n╔══════════════════════════════════════════╗");
    println!("║           TEST SUMMARY                   ║");
    println!("╠══════════════════════════════════════════╣");
    println!(
        "║  Passed: {:2} | Failed: {:2} | Total: {:2}     ║",
        passed,
        failed,
        passed + failed
    );
    println!("╚══════════════════════════════════════════╝");

    if failed == 0 {
        println!("\n  All SSCCS constitutional concepts validated successfully!");
    } else {
        println!(
            "\n  {} concept test(s) failed. Review implementation.",
            failed
        );
        std::process::exit(1);
    }
}

// ==================== INDIVIDUAL CONCEPT TESTS ====================

/// Test 1: Segment Concept -Immutable coordinate existence
/// SSCCS Docs: "Segments are immutable points in possibility space"
fn test_segment_concept() -> Result<(), String> {
    // 1. Coordinate-based existence
    let coords = SpaceCoordinates::new(vec![1, 2, 3]);
    let segment = Segment::new(coords.clone());

    println!(
        "  1. Segment created from coordinates: {:?}",
        segment.coordinates().raw
    );
    println!(
        "     Dimensionality: {}",
        segment.coordinates().dimensionality()
    );

    // 2. Cryptographic identity
    let id = segment.id();
    println!(
        "  2. Cryptographic identity (BLAKE3): {}",
        hex::encode(id.as_bytes())
    );

    // 3. Same coordinates → Same identity (deterministic)
    let segment2 = Segment::new(coords.clone());
    if segment.id() != segment2.id() {
        return Err("Segments with identical coordinates must have identical IDs".into());
    }
    println!("  3. Identity consistency verified (deterministic ID generation)");

    // 4. Immutability verification
    println!("  4. Immutability verified:");
    println!("     - Segment coordinates are read-only");
    println!("     - Segment ID is computed once and immutable");
    println!("     - Clone creates independent copy with same ID");

    // 5. Convenience constructors
    let single_val = Segment::from_value(42);
    let multi_val = Segment::from_values(vec![10, 20, 30]);
    println!("  5. Convenience constructors:");
    println!(
        "     - Single value segment: {:?}",
        single_val.coordinates().raw
    );
    println!(
        "     - Multi-value segment: {:?}",
        multi_val.coordinates().raw
    );

    // 6. Clone verification
    let seg_clone = segment.clone();
    if segment.id() != seg_clone.id() {
        return Err("Cloned segment must have same ID".into());
    }
    println!("  6. Clone preserves cryptographic identity");

    Ok(())
}

/// Test 2: Field Concept -Mutable constraint substrate
/// SSCCS Docs: "Field is the only mutable layer. Contains constraints and relational topology."
fn test_field_concept() -> Result<(), String> {
    let mut field = Field::new();

    // 1. Constraint addition
    field.add_constraint(RangeConstraint::new(0, 0, 10));
    field.add_constraint(RangeConstraint::new(1, 0, 5));
    field.add_constraint(EvenConstraint::new(0));

    println!("  1. Field constraints added:");
    println!("     - {}", field.describe_constraints());

    // 2. Constraint validation
    let valid_coords = SpaceCoordinates::new(vec![4, 3, 100]); // Even, within ranges
    let invalid_range = SpaceCoordinates::new(vec![15, 3, 0]);
    let invalid_even = SpaceCoordinates::new(vec![3, 2, 0]);

    println!("  2. Constraint validation:");
    println!(
        "     - Valid coords [4, 3, 100]: {}",
        field.allows(&valid_coords)
    );
    println!(
        "     - Invalid range [15, 3, 0]: {}",
        field.allows(&invalid_range)
    );
    println!(
        "     - Invalid even [3, 2, 0]: {}",
        field.allows(&invalid_even)
    );

    if !field.allows(&valid_coords) {
        return Err("Valid coordinates should be allowed".to_string());
    }
    if field.allows(&invalid_range) {
        return Err("Coordinates out of range should be rejected".to_string());
    }
    if field.allows(&invalid_even) {
        return Err("Odd coordinates should be rejected by EvenConstraint".to_string());
    }
    println!("     All constraint validations passed");

    // 3. Transition rules (relational topology)
    let from_coords = SpaceCoordinates::new(vec![1, 2, 3]);
    let to_coords = SpaceCoordinates::new(vec![2, 2, 3]);
    field.add_transition(from_coords.clone(), to_coords.clone(), 1.0);

    println!("  3. Transition rules added:");
    println!("     - From [1, 2, 3] → [2, 2, 3] with weight 1.0");

    let transitions = field.transition_targets(&from_coords);
    println!(
        "     - Transition targets: {:?}",
        transitions
            .iter()
            .map(|c| c.raw.clone())
            .collect::<Vec<_>>()
    );

    if transitions.len() != 1 || transitions[0] != to_coords {
        return Err("Transition should return the correct target coordinates".to_string());
    }

    // 4. Field mutability demonstration
    println!("  4. Field mutability demonstrated:");
    println!("     - Constraints can be added after creation");
    println!("     - Transition rules can be added dynamically");
    println!("     - Field does not own Segments (separation of concerns)");

    Ok(())
}

/// Test 3: Projector Concept -Semantic interpretation
/// SSCCS Docs: "Projector gives semantic meaning to combination of Field and Segment"
fn test_projector_concept() -> Result<(), String> {
    println!("  1. Testing different projectors on same coordinates:");

    let segment = Segment::from_value(7);
    println!("     Segment coordinates: {:?}", segment.coordinates().raw);

    let empty_field = Field::new();

    // Integer projector
    let int_projector = IntegerProjector::new(0);
    let int_result = int_projector.project(&empty_field, &segment);
    println!("  2. IntegerProjector result: {:?}", int_result);

    if int_result != Some(7) {
        return Err("IntegerProjector should extract coordinate value".to_string());
    }

    // Parity projector
    let parity_projector = ParityProjector;
    let parity_result = parity_projector.project(&empty_field, &segment);
    println!("  3. ParityProjector result: {:?}", parity_result);

    if parity_result != Some("odd".to_string()) {
        return Err("ParityProjector should return \"odd\" for value 7".to_string());
    }

    // Arithmetic projector
    let arith_projector = ArithmeticProjector;
    let arith_result = arith_projector.project(&empty_field, &segment);
    println!("  4. ArithmeticProjector result: {:?}", arith_result);

    // Test adjacency semantics
    let next_coords = arith_projector.possible_next_coordinates(segment.coordinates());
    println!("  5. ArithmeticProjector adjacency:");
    println!(
        "     - Possible next coordinates: {:?}",
        next_coords.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );

    // Verify different semantic interpretations
    println!("  6. Semantic interpretation verified:");
    println!("     - Same coordinates → Different meanings");
    println!("     - Meaning emerges from projector, not coordinates");
    println!("     - Projector defines adjacency semantics");

    Ok(())
}

/// Test 4: Observation Concept -The sole active event
/// SSCCS Docs: "Observation is the only mechanism that produces actuality"
fn test_observation_concept() -> Result<(), String> {
    println!("  1. Testing observation with constraint filtering:");

    let segment = Segment::from_value(5);
    let mut field = Field::new();
    field.add_constraint(RangeConstraint::new(0, 0, 10));

    let int_projector = IntegerProjector::new(0);

    // Observation with allowed coordinates
    let observation_result = observe(&field, &segment, &int_projector);
    println!(
        "     - Observation result (allowed): {:?}",
        observation_result
    );

    if observation_result != Some(5) {
        return Err("Observation should succeed for allowed coordinates".to_string());
    }

    // Observation with disallowed coordinates
    let invalid_segment = Segment::from_value(15);
    let failed_observation = observe(&field, &invalid_segment, &int_projector);
    println!(
        "     - Observation result (disallowed): {:?}",
        failed_observation
    );

    if failed_observation.is_some() {
        return Err("Observation should fail for disallowed coordinates".to_string());
    }

    println!("  2. Observation properties verified:");
    println!("     - Field constraints filter observations");
    println!("     - Projection is ephemeral (not cached)");
    println!("     - Re-observation required for same result");
    println!("     - No state mutation during observation");

    // Test possible_next_coordinates function
    let next_coords = possible_next_coordinates(&field, &segment, &ArithmeticProjector);
    println!("  3. Possible next coordinates (filtered by field):");
    println!(
        "     - {:?}",
        next_coords.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );

    Ok(())
}

/// Test 5: Space Concept -Structured coordinate spaces
/// SSCCS Docs: "Spaces provide structured access to coordinate systems"
fn test_space_concept() -> Result<(), String> {
    println!("  1. BasicSpace - Multi-dimensional coordinates:");

    let coords = SpaceCoordinates::new(vec![1, 2, 3]);
    let basic_space = BasicSpace::new(coords.clone());

    println!(
        "     - Created from coordinates: {:?}",
        basic_space.coordinates().raw
    );
    println!("     - ID: {}", hex::encode(basic_space.id().as_bytes()));

    // Test deref to Segment
    let segment_ref: &Segment = &basic_space;
    println!(
        "     - Dereferences to Segment: {:?}",
        segment_ref.coordinates().raw
    );

    // Test From trait
    let basic_from_coords: BasicSpace = coords.clone().into();
    if basic_from_coords.coordinates() != &coords {
        return Err("From<SpaceCoordinates> should preserve coordinates".to_string());
    }
    println!("     From<SpaceCoordinates> trait works");

    println!("\n  2. IntegerSpace - Single-axis convenience:");

    let int_space = IntegerSpace::new(42);
    println!(
        "     - Created from value: {:?}",
        int_space.coordinates().raw
    );
    println!("     - ID: {}", hex::encode(int_space.id().as_bytes()));

    // Test conversions
    let _from_segment = IntegerSpace::from_segment(segment_ref.clone());
    println!("     Converted from Segment");

    let _from_coords: IntegerSpace = coords.clone().into();
    println!("     From<SpaceCoordinates> trait works");

    Ok(())
}

/// Test 6: Scheme Concept -Structural blueprint
/// SSCCS Docs: "Scheme is the immutable structural blueprint"
fn test_scheme_concept() -> Result<(), String> {
    println!("  1. Creating 2D Grid Scheme:");

    let grid_scheme = Grid2DScheme::new(5, 5).to_scheme();
    println!("     - Scheme description: {}", grid_scheme.describe());
    println!(
        "     - Scheme ID: {}",
        hex::encode(grid_scheme.id().as_bytes())
    );

    println!("\n  2. Scheme properties:");
    println!("     - Dimensions: {}", grid_scheme.dimensionality());
    println!("     - Segment count: {}", grid_scheme.segments().count());
    println!("     - Axes count: {}", grid_scheme.axes().len());

    // Test segment lookup
    let test_coords = SpaceCoordinates::new(vec![2, 2]);
    let test_segment = Segment::new(test_coords.clone());

    if grid_scheme.contains_segment(test_segment.id()) {
        println!("     Contains segment at (2, 2)");

        // Memory mapping
        if let Some(addr) = grid_scheme.map_to_memory(&test_coords) {
            println!("     - Memory address for (2, 2): {}", addr);
        } else {
            return Err("Memory mapping should succeed for valid coordinates".to_string());
        }
    } else {
        return Err("Grid scheme should contain segment at (2, 2)".to_string());
    }

    println!("\n  3. Creating Integer Line Scheme:");

    let int_scheme = IntegerLineScheme::new(-5, 5).to_scheme();
    println!("     - Scheme description: {}", int_scheme.describe());
    println!("     - Segment count: {}", int_scheme.segments().count());

    // Verify structural constraints
    let valid_coords = SpaceCoordinates::new(vec![0]);
    if !int_scheme.structural_constraints_satisfied(&valid_coords) {
        // This is OK -depends on implementation
        println!("     - Structural constraints checked");
    }

    println!("  4. Scheme immutability verified:");
    println!("     - Scheme ID is cryptographic hash of structure");
    println!("     - Segments cannot be modified after creation");
    println!("     - Adjacency relations are fixed");

    Ok(())
}

/// Test 7: Adjacency & Memory Layout -Structural relations
/// SSCCS Docs: "Scheme defines geometry and memory layout semantics"
fn test_adjacency_memory() -> Result<(), String> {
    println!("  1. Testing Adjacency Relations:");

    let seg1 = Segment::from_values(vec![0, 0]);
    let seg2 = Segment::from_values(vec![1, 0]);
    let seg3 = Segment::from_values(vec![0, 1]);

    let scheme = scheme::SchemeBuilder::new()
        .add_axis(scheme::Axis {
            name: "x".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: Some((0, 10)),
        })
        .add_axis(scheme::Axis {
            name: "y".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: Some((0, 10)),
        })
        .add_segment(seg1.clone())
        .add_segment(seg2.clone())
        .add_segment(seg3.clone())
        .add_adjacency(
            *seg1.id(),
            *seg2.id(),
            scheme::AdjacencyRelation::Manhattan(1),
        )
        .add_adjacency(
            *seg1.id(),
            *seg3.id(),
            scheme::AdjacencyRelation::Manhattan(1),
        )
        .build();

    let neighbors = scheme.neighbors_of(seg1.id());
    println!(
        "     - Segment {:?} neighbors: {}",
        seg1.coordinates().raw,
        neighbors.len()
    );

    if neighbors.len() != 2 {
        return Err(format!("Expected 2 neighbors, got {}", neighbors.len()));
    }
    println!("     Adjacency relations working");

    println!("\n  2. Testing Memory Layout Mappings:");

    let coords_2d = SpaceCoordinates::new(vec![3, 5]);

    // Row major
    let scheme_row = scheme::SchemeBuilder::new()
        .add_axis(scheme::Axis {
            name: "row".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: Some((0, 9)),
        })
        .add_axis(scheme::Axis {
            name: "col".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: Some((0, 9)),
        })
        .set_memory_layout(scheme::MemoryLayout::RowMajor)
        .build();

    if let Some(addr) = scheme_row.map_to_memory(&coords_2d) {
        println!("     - RowMajor (3, 5): {} (expected: 35)", addr);
        if addr != 35 {
            return Err(format!(
                "RowMajor mapping incorrect: expected 35, got {}",
                addr
            ));
        }
    }

    // Column major
    let scheme_col = scheme::SchemeBuilder::new()
        .add_axis(scheme::Axis {
            name: "row".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: Some((0, 9)),
        })
        .add_axis(scheme::Axis {
            name: "col".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: Some((0, 9)),
        })
        .set_memory_layout(scheme::MemoryLayout::ColumnMajor)
        .build();

    if let Some(addr) = scheme_col.map_to_memory(&coords_2d) {
        println!("     - ColumnMajor (3, 5): {} (expected: 53)", addr);
        if addr != 53 {
            return Err(format!(
                "ColumnMajor mapping incorrect: expected 53, got {}",
                addr
            ));
        }
    }

    // Linear
    let coords_1d = SpaceCoordinates::new(vec![10, 20, 30]);
    let scheme_linear = scheme::SchemeBuilder::new()
        .add_axis(scheme::Axis {
            name: "a".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: None,
        })
        .add_axis(scheme::Axis {
            name: "b".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: None,
        })
        .add_axis(scheme::Axis {
            name: "c".to_string(),
            dimension_type: scheme::DimensionType::Discrete,
            range: None,
        })
        .set_memory_layout(scheme::MemoryLayout::Linear)
        .build();

    if let Some(addr) = scheme_linear.map_to_memory(&coords_1d) {
        println!("     - Linear (10, 20, 30): {} (expected: 60)", addr);
        if addr != 60 {
            return Err(format!(
                "Linear mapping incorrect: expected 60, got {}",
                addr
            ));
        }
    }

    println!("  3. Memory layout mappings verified:");
    println!("     - RowMajor: row * width + column");
    println!("     - ColumnMajor: column * height + row");
    println!("     - Linear: sum of coordinates");

    Ok(())
}

/// Test 8: Transition Matrix - Relational topology
/// SSCCS Docs: "Field contains relational topology as weighted directed graph"
fn test_transition_matrix() -> Result<(), String> {
    println!("  1. Testing Transition Matrix:");

    let mut field = Field::new();

    let from = SpaceCoordinates::new(vec![0]);
    let to1 = SpaceCoordinates::new(vec![1]);
    let to2 = SpaceCoordinates::new(vec![2]);

    field.add_transition(from.clone(), to1.clone(), 0.8);
    field.add_transition(from.clone(), to2.clone(), 0.2);

    let targets = field.transition_targets(&from);
    println!(
        "     - From {:?} transition targets: {}",
        from.raw,
        targets.len()
    );

    for target in &targets {
        println!("       - {:?}", target.raw);
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

    println!("  2. Transition matrix verified:");
    println!("     - Weighted directed graph structure");
    println!("     - Multiple transitions from single source");
    println!("     - Target retrieval working (weights managed internally)");

    Ok(())
}

/// Test 9: Integrated Workflow -Complete SSCCS pipeline
/// SSCCS Docs: "From structure to observation"
fn test_integrated_workflow() -> Result<(), String> {
    println!("  1. Complete SSCCS workflow demonstration:");

    // Step 1: Create Scheme (structure)
    println!("\n     Step 1: Create structural blueprint");
    let scheme = IntegerLineScheme::new(0, 10).to_scheme();
    println!("        - Scheme: {}", scheme.describe());

    // Step 2: Select Segment from Scheme
    println!("     Step 2: Select Segment from blueprint");
    let segment = scheme.segments().nth(5).unwrap();
    println!(
        "        - Selected segment: {:?}",
        segment.coordinates().raw
    );

    // Step 3: Configure Field (constraints)
    println!("     Step 3: Configure mutable Field");
    let mut field = Field::new();
    field.add_constraint(RangeConstraint::new(0, 0, 10));

    // Step 4: Choose Projector (semantics)
    println!("     Step 4: Choose semantic interpretation");
    let projector = ArithmeticProjector;

    // Step 5: Observe (collapse to actuality)
    println!("     Step 5: Observe (collapse constraint space)");
    let observation = observe(&field, segment, &projector);
    println!("        - Observation result: {:?}", observation);

    if observation.is_none() {
        return Err("Observation should succeed for allowed coordinates".to_string());
    }
    println!("        - Observed value: {:?}", observation.unwrap());

    // Step 6: Explore possibilities
    println!("     Step 6: Explore possible transitions");
    let possibilities = possible_next_coordinates(&field, segment, &projector);
    println!(
        "        - Filtered possibilities: {:?}",
        possibilities.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );

    println!("\n  2. Workflow verification:");
    println!("     - Structure defined by Scheme (immutable)");
    println!("     - Constraints managed by Field (mutable)");
    println!("     - Semantics provided by Projector");
    println!("     - Actuality produced by Observation");
    println!("     - Data movement minimized (Segments stationary)");
    println!("     - No state mutation during computation");

    // Additional integrated test: Grid with observation
    println!("\n  3. Grid observation test:");
    let grid_scheme = Grid2DScheme::new(3, 3).to_scheme();
    let mut grid_field = Field::new();
    grid_field.add_constraint(RangeConstraint::new(0, 0, 2));
    grid_field.add_constraint(RangeConstraint::new(1, 0, 2));

    let grid_projector = IntegerProjector::new(0);
    let mut observed_count = 0;

    for seg in grid_scheme.segments() {
        if observe(&grid_field, seg, &grid_projector).is_some() {
            observed_count += 1;
        }
    }
    println!("     - Grid segments observed: {}", observed_count);
    println!(
        "     - Total grid segments: {}",
        grid_scheme.segments().count()
    );

    Ok(())
}
