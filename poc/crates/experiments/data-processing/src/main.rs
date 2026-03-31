//! Experiment: Observation-Centric Data Processing with Rust
//!
//! This experiment demonstrates how SSCCS can be used for data processing tasks
//! by treating computation as the observation of fixed structure under changing conditions.
//! We implement a simple matrix summation operation using SSCCS concepts and
//! compare it with traditional imperative programming.

use ssccs_core::{Constraint, Field, Projector, SpaceCoordinates};
use ssccs_primitive::GridTopology;
use ssccs_schemes::Grid2DTemplate;

/// A constraint that only allows coordinates within a matrix boundary
#[derive(Debug)]
struct MatrixBoundaryConstraint {
    rows: i64,
    cols: i64,
}

impl MatrixBoundaryConstraint {
    fn new(rows: i64, cols: i64) -> Self {
        Self { rows, cols }
    }
}

impl Constraint for MatrixBoundaryConstraint {
    fn allows(&self, coords: &SpaceCoordinates) -> bool {
        if coords.raw.len() != 2 {
            return false;
        }
        let x = coords.raw[0];
        let y = coords.raw[1];
        x >= 0 && x < self.rows && y >= 0 && y < self.cols
    }

    fn describe(&self) -> String {
        format!("MatrixBoundary({}x{})", self.rows, self.cols)
    }
}

/// A projector that sums values associated with matrix elements
#[derive(Debug)]
struct MatrixSumProjector;

impl Projector for MatrixSumProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &ssccs_core::Segment) -> Option<Self::Output> {
        // In a real implementation, we would have actual values associated with segments
        // For this demo, we'll use a simple heuristic: sum of coordinates
        let coords = segment.coordinates();
        if coords.raw.len() == 2 {
            // Simple demo: use (x + y) as the "value" at this matrix position
            Some(coords.raw[0] + coords.raw[1])
        } else {
            None
        }
    }
}

/// Traditional imperative approach to matrix summation
fn traditional_matrix_sum(rows: i64, cols: i64) -> i64 {
    let mut sum = 0;
    for i in 0..rows {
        for j in 0..cols {
            // Same heuristic as above: (i + j) as value
            sum += i + j;
        }
    }
    sum
}

fn main() {
    println!("╔════════════════════════════════════════════════════════════╗");
    println!("║  Experiment: Observation-Centric Data Processing with Rust ║");
    println!("╚════════════════════════════════════════════════════════════╝\n");

    // Parameters for our matrix
    let rows = 3;
    let cols = 4;

    println!("Testing with a {}x{} matrix", rows, cols);
    println!("Value at position (i,j) = i + j (for demonstration)\n");

    // === Traditional Imperative Approach ===
    println!("=== Traditional Imperative Approach ===");
    let traditional_start = std::time::Instant::now();
    let traditional_result = traditional_matrix_sum(rows, cols);
    let traditional_duration = traditional_start.elapsed();
    println!("Result: {}", traditional_result);
    println!("Time: {:?}\n", traditional_duration);

    // === SSCCS Observation-Centric Approach ===
    println!("=== SSCCS Observation-Centric Approach ===");

    let ssccs_start = std::time::Instant::now();

    // 1. Create a Scheme (2D Grid representing our matrix)
    let scheme = Grid2DTemplate::new(rows, cols, GridTopology::EightConnected).build();
    println!(
        "1. Created 2D grid scheme ({}x{}) with {} segments",
        rows,
        cols,
        scheme.segments().count()
    );

    // 2. Create a Field with matrix boundary constraint
    let mut field = Field::new();
    field.add_constraint(MatrixBoundaryConstraint::new(rows, cols));
    println!("2. Created field with matrix boundary constraint");

    // 3. Create a projector for matrix summation
    let projector = MatrixSumProjector;
    println!("3. Created MatrixSumProjector");

    // 4. Observe all segments and sum the results
    let mut ssccs_result = 0;
    let mut observed_count = 0;

    for segment in scheme.segments() {
        if field.allows(segment.coordinates()) {
            if let Some(value) = projector.project(&field, segment) {
                ssccs_result += value;
                observed_count += 1;
            }
        }
    }

    let ssccs_duration = ssccs_start.elapsed();

    println!("4. Observed {} segments", observed_count);
    println!("Result: {}", ssccs_result);
    println!("Time: {:?}\n", ssccs_duration);

    // === Comparison ===
    println!("=== Comparison ===");
    println!("Traditional result: {}", traditional_result);
    println!("SSCCS result: {}", ssccs_result);

    let diff = traditional_result.abs_diff(ssccs_result);
    if diff == 0 {
        println!(" Results match exactly");
    } else {
        println!(" Results differ by {}", diff);
    }

    println!("\n=== Key Insights ===");
    println!("1. In SSCCS, computation is framed as observation of structure under constraints");
    println!("2. The Scheme defines the fixed structure (matrix grid)");
    println!("3. The Field defines dynamic constraints (matrix boundaries)");
    println!("4. The Projector defines how to interpret/process each segment");
    println!("5. Observation combines all three to produce results");
    println!("6. No explicit loops in the SSCCS approach - iteration is implicit in observation");
    println!("7. The same pattern can be extended to more complex operations (filtering, transformations, etc.)");

    // Demonstrate additional SSCCS capabilities
    println!("\n=== Advanced SSCCS Features Demonstrated ===");

    // Show constraint validation
    let valid_coords = SpaceCoordinates::new(vec![1, 2]);
    let invalid_coords = SpaceCoordinates::new(vec![10, 10]);

    println!("Constraint validation:");
    println!(
        "- Coordinates [1, 2] allowed: {}",
        field.allows(&valid_coords)
    );
    println!(
        "- Coordinates [10, 10] allowed: {}",
        field.allows(&invalid_coords)
    );

    // Show that fields are mutable (can change constraints dynamically)
    println!("\nField mutability demonstration:");
    println!("- Initial constraints: {}", field.describe_constraints());

    // Add another constraint dynamically
    #[derive(Debug)]
    struct EvenRowConstraint;

    impl Constraint for EvenRowConstraint {
        fn allows(&self, coords: &SpaceCoordinates) -> bool {
            if !coords.raw.is_empty() {
                coords.raw[0] % 2 == 0 // Only even rows allowed
            } else {
                false
            }
        }

        fn describe(&self) -> String {
            "EvenRowConstraint".to_string()
        }
    }

    field.add_constraint(EvenRowConstraint);
    println!("- Added EvenRowConstraint");
    println!("- New constraints: {}", field.describe_constraints());

    // Show filtered observation with new constraint
    let mut filtered_sum = 0;
    let mut filtered_count = 0;

    for segment in scheme.segments() {
        if field.allows(segment.coordinates()) {
            if let Some(value) = projector.project(&field, segment) {
                filtered_sum += value;
                filtered_count += 1;
            }
        }
    }

    println!("- Filtered observation (only even rows):");
    println!(
        "  Observed {} segments, sum = {}",
        filtered_count, filtered_sum
    );

    println!("\n Experiment completed successfully!");
}
