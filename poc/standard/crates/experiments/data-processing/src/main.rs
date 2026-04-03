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

/// A projector that looks up pre‑computed values for each matrix element
#[derive(Debug)]
struct MatrixValueProjector {
    rows: i64,
    cols: i64,
    values: Vec<i64>, // row‑major storage: values[(row * cols) + col]
}

impl MatrixValueProjector {
    fn new(rows: i64, cols: i64, values: Vec<i64>) -> Self {
        assert_eq!(values.len(), (rows * cols) as usize);
        Self { rows, cols, values }
    }

    fn get(&self, row: i64, col: i64) -> Option<i64> {
        if row >= 0 && row < self.rows && col >= 0 && col < self.cols {
            let idx = (row * self.cols + col) as usize;
            Some(self.values[idx])
        } else {
            None
        }
    }
}

impl Projector for MatrixValueProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &ssccs_core::Segment) -> Option<Self::Output> {
        let coords = segment.coordinates();
        if coords.raw.len() == 2 {
            let row = coords.raw[0];
            let col = coords.raw[1];
            self.get(row, col)
        } else {
            None
        }
    }
}

/// Generate a matrix of random i64 values
fn generate_random_matrix(rows: i64, cols: i64) -> Vec<i64> {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    let size = (rows * cols) as usize;
    (0..size).map(|_| rng.gen_range(0..1000)).collect()
}

/// Traditional imperative summation of a pre‑computed value matrix
fn traditional_matrix_sum_with_values(rows: i64, cols: i64, values: &[i64]) -> i64 {
    let mut sum = 0;
    for i in 0..rows {
        for j in 0..cols {
            let idx = (i * cols + j) as usize;
            sum += values[idx];
        }
    }
    sum
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
    println!("Experiment: Observation-Centric Data Processing with Rust ");

    // Parameters for our matrix
    let rows = 3;
    let cols = 4;

    println!("Testing with a {}x{} matrix", rows, cols);
    println!("Value at position (i,j) = i + j (for demonstration)\n");

    // === Traditional Imperative Approach ===
    println!("Traditional Imperative Approach");
    let traditional_start = std::time::Instant::now();
    let traditional_result = traditional_matrix_sum(rows, cols);
    let traditional_duration = traditional_start.elapsed();
    println!("Result: {}", traditional_result);
    println!("Time: {:?}\n", traditional_duration);

    // === SSCCS Observation-Centric Approach ===
    println!("SSCCS Observation-Centric Approach");

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
    println!("Comparison");
    println!("Traditional result: {}", traditional_result);
    println!("SSCCS result: {}", ssccs_result);

    let diff = traditional_result.abs_diff(ssccs_result);
    if diff == 0 {
        println!("Results match exactly");
    } else {
        println!("Results differ by {}", diff);
    }

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
    println!("Added EvenRowConstraint");
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

    println!("Filtered observation (only even rows):");
    println!(
        "  Observed {} segments, sum = {}",
        filtered_count, filtered_sum
    );

    // ============================================
    // Large‑Scale Benchmark (100×100 matrix)
    // ============================================
    println!("Large‑Scale Benchmark (100×100 random matrix)       ");

    let large_rows = 100;
    let large_cols = 100;

    // Generate random values
    let large_values = generate_random_matrix(large_rows, large_cols);

    // Traditional approach
    let traditional_start = std::time::Instant::now();
    let traditional_sum = traditional_matrix_sum_with_values(large_rows, large_cols, &large_values);
    let traditional_duration = traditional_start.elapsed();

    // SSCCS approach
    let ssccs_start = std::time::Instant::now();
    let scheme = Grid2DTemplate::new(large_rows, large_cols, GridTopology::EightConnected).build();
    let mut field = Field::new();
    field.add_constraint(MatrixBoundaryConstraint::new(large_rows, large_cols));
    let projector = MatrixValueProjector::new(large_rows, large_cols, large_values.clone());

    let mut ssccs_sum = 0;
    for segment in scheme.segments() {
        if field.allows(segment.coordinates()) {
            if let Some(value) = projector.project(&field, segment) {
                ssccs_sum += value;
            }
        }
    }
    let ssccs_duration = ssccs_start.elapsed();

    println!(
        "Traditional sum: {} (time: {:?})",
        traditional_sum, traditional_duration
    );
    println!("SSCCS sum: {} (time: {:?})", ssccs_sum, ssccs_duration);
    println!(
        "Speed ratio: {:.2}x",
        traditional_duration.as_secs_f64() / ssccs_duration.as_secs_f64()
    );

    println!("\n Experiment completed successfully!");
}
