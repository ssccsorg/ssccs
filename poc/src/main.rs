use ssccs_poc::core::{Field, Projector, Segment, SpaceCoordinates};
use ssccs_poc::spaces::{arithmetic::IntegerSpace, basic::BasicSpace};
use ssccs_poc::*;

// A simple projector that extracts a single axis value.
#[derive(Debug, Clone)]
struct IntegerProjector {
    axis: usize,
}

impl IntegerProjector {
    fn new(axis: usize) -> Self {
        Self { axis }
    }
}

impl Projector for IntegerProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(self.axis)
    }

    // No intrinsic adjacency for this projector.
}

// A projector that performs arithmetic operations to generate neighbours.
#[derive(Debug, Clone)]
struct ArithmeticProjector;

impl Projector for ArithmeticProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(0)
    }

    fn possible_next_coordinates(&self, coords: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        let current = coords.get_axis(0).unwrap_or(0);
        vec![
            SpaceCoordinates::new(vec![current + 1]),
            SpaceCoordinates::new(vec![current - 1]),
            SpaceCoordinates::new(vec![current * 2]),
            SpaceCoordinates::new(vec![current / 2]), // integer division
        ]
    }
}

// A projector that returns a string based on parity.
#[derive(Debug, Clone)]
struct ParityProjector;

impl Projector for ParityProjector {
    type Output = String;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let coord = segment.coordinates().get_axis(0)?;
        if coord % 2 == 0 {
            Some("even".into())
        } else {
            Some("odd".into())
        }
    }
}

fn main() {
    println!("SSCCS Proof of Concept");
    println!("=======================================================\n");

    // 1. Create immutable SchemaSegments
    let coords = SpaceCoordinates::new(vec![1, 2, 3]);
    let basic_segment = BasicSpace::new(coords.clone());
    println!(
        "BasicSegment coordinates: {:?}",
        basic_segment.coordinates().raw
    );
    println!("BasicSegment identity: {:?}", basic_segment.id().as_bytes());
    println!();

    let arith_segment = IntegerSpace::new(5);
    println!("IntegerSegment at {:?}", arith_segment.coordinates().raw);
    println!(
        "IntegerSegment identity: {:?}",
        arith_segment.id().as_bytes()
    );
    println!();

    // 2. Create a mutable Field and add constraints
    let mut field = Field::new();
    field.add_constraint(RangeConstraint::new(0, 0, 10));
    field.add_constraint(RangeConstraint::new(1, 0, 5));
    field.add_transition(
        SpaceCoordinates::new(vec![1, 2, 3]),
        SpaceCoordinates::new(vec![2, 2, 3]),
        1.0,
    );
    println!("Field constraints: {}", field.describe_constraints());
    println!(
        "BasicSegment allowed? {}",
        field.allows(basic_segment.coordinates())
    );
    println!();

    // 3. Observe using different projectors
    let int_projector = IntegerProjector::new(0);
    if let Some(val) = observe(&field, &basic_segment, &int_projector) {
        println!("Observation (IntegerProjector): {}", val);
    } else {
        println!("Observation failed (coordinate not allowed)");
    }

    let parity_proj = ParityProjector;
    if let Some(parity) = observe(&field, &basic_segment, &parity_proj) {
        println!("Observation (ParityProjector): {}", parity);
    }
    println!();

    // 4. Explore possible next coordinates using ArithmeticProjector
    let arith_proj = ArithmeticProjector;
    let next_coords = possible_next_coordinates(&field, &basic_segment, &arith_proj);
    println!("Possible next coordinates (ArithmeticProjector + field transitions, filtered):");
    for coord in &next_coords {
        println!("  {:?}", coord.raw);
    }
    println!();

    // 5. Work with arithmetic segment
    let mut arith_field = Field::new();
    arith_field.add_constraint(RangeConstraint::new(0, 0, 20));
    arith_field.add_constraint(EvenConstraint::new(0));

    println!(
        "Arithmetic field constraints: {}",
        arith_field.describe_constraints()
    );
    println!(
        "IntegerSegment allowed? {}",
        arith_field.allows(arith_segment.coordinates())
    );

    if let Some(val) = observe(&arith_field, &arith_segment, &IntegerProjector::new(0)) {
        println!("Observed value: {}", val);
    }

    let next_arith = possible_next_coordinates(&arith_field, &arith_segment, &arith_proj);
    println!(
        "Possible next values (ArithmeticProjector, filtered by even constraint): {:?}",
        next_arith.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );
    println!();

    // 6. Demonstrate that projections are ephemeral
    println!("Projections are ephemeral: they are returned but not cached by the core.");
    println!("If you need a projection again, you must observe again.");
    println!();

    // 7. Time as just another coordinate (conceptual)
    println!("Time is just another coordinate. To model a temporal sequence,");
    println!("include a time axis in your coordinates and compare values on that axis.");
    println!("For example, coordinates [t, x, y] with t as time.");
    println!();

    println!(
        "SSCCS PoC now fully aligns: segments are pure coordinates, meaning is projected by projectors."
    );
}
