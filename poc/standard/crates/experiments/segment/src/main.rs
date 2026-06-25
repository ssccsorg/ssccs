use ssccs_core::{Coordinates, Field, Projector, Segment};

#[derive(Debug, Clone)]
struct IdentityProjector;

impl Projector for IdentityProjector {
    type Output = i64;
    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        Some(segment.coordinates().get_axis(0).unwrap_or(0))
    }
    fn possible_next_coordinates(&self, _coords: &Coordinates) -> Vec<Coordinates> {
        Vec::new()
    }
}

fn main() {
    let field = Field::new(); // no constraints
    let projector = IdentityProjector;
    let test_coords = vec![0i64, 2, 4, 6, 8, 10];

    println!("=== SSCCS Rust: experiment-01-segment ===");
    println!("Field: no constraints");
    println!("Projector: identity\n");

    let mut passed = 0;
    let mut failed = 0;

    for &coord in &test_coords {
        let segment = Segment::from_value(coord);
        let result = ssccs_core::observe(&field, &segment, &projector);
        let ok = result == Some(coord);
        if ok {
            println!("PASS: observe(coord={}) == {}", coord, coord);
            passed += 1;
        } else {
            println!(
                "FAIL: observe(coord={}) expected {}, got {:?}",
                coord, coord, result
            );
            failed += 1;
        }
    }

    println!("\nTotal:  {}", passed + failed);
    println!("Passed: {}", passed);
    println!("Failed: {}", failed);
}
