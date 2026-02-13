use ssccs_poc::core::{Field, Projector, SchemeSegment, SpaceCoordinates};
use ssccs_poc::spaces::{arithmetic::ArithmeticSpace, basic::BasicSpace};
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

    fn project(&self, _field: &Field, segment: &dyn SchemeSegment) -> Option<Self::Output> {
        // For this simple projector, we ignore the field and just return the coordinate value.
        // But we do check that the coordinate is allowed (already done by `observe`).
        segment.coordinates().get_axis(self.axis)
    }
}

// A projector that returns a string based on parity (demonstrates using field).
#[derive(Debug, Clone)]
struct ParityProjector;

impl Projector for ParityProjector {
    type Output = String;

    fn project(&self, _field: &Field, segment: &dyn SchemeSegment) -> Option<Self::Output> {
        let coord = segment.coordinates().get_axis(0)?;
        if coord % 2 == 0 {
            Some("even".into())
        } else {
            Some("odd".into())
        }
    }
}

fn main() {
    println!("SSCCS Proof of Concept (Constitution‑Compliant Rewrite)");
    println!("=======================================================\n");

    // 1. Create an immutable SchemaSegment
    let coords = SpaceCoordinates::new(vec![1, 2, 3]);
    let basic_segment = BasicSpace::new(coords.clone());
    println!("Segment coordinates: {:?}", basic_segment.coordinates().raw);
    println!(
        "Segment identity: {:?}",
        basic_segment.identity().as_bytes()
    );
    println!(
        "Basic adjacency: {:?}",
        basic_segment
            .basic_adjacency()
            .iter()
            .map(|c| &c.raw)
            .collect::<Vec<_>>()
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
        "Segment allowed? {}",
        field.allows(&basic_segment.coordinates())
    );
    println!();

    // 3. Observe using a projector
    let projector = IntegerProjector::new(0);
    if let Some(val) = observe(&field, &basic_segment, &projector) {
        println!("Observation (IntegerProjector): {}", val);
    } else {
        println!("Observation failed (coordinate not allowed)");
    }

    // 4. Use a projector that incorporates field information
    let parity_proj = ParityProjector;
    if let Some(parity) = observe(&field, &basic_segment, &parity_proj) {
        println!("Observation (ParityProjector): {}", parity);
    }
    println!();

    // 5. Explore possible next coordinates
    let next_coords = possible_next_coordinates(&field, &basic_segment);
    println!("Possible next coordinates (structural + field transitions, filtered):");
    for coord in &next_coords {
        println!("  {:?}", coord.raw);
    }
    println!();

    // 6. Work with a different segment type
    let arith_segment = ArithmeticSpace::new(5);
    println!(
        "Arithmetic segment at {:?}",
        arith_segment.coordinates().raw
    );
    println!(
        "Arithmetic identity: {:?}",
        arith_segment.identity().as_bytes()
    );
    println!(
        "Arithmetic basic adjacency: {:?}",
        arith_segment
            .basic_adjacency()
            .iter()
            .map(|c| c.raw[0])
            .collect::<Vec<_>>()
    );

    let mut arith_field = Field::new();
    arith_field.add_constraint(RangeConstraint::new(0, 0, 20));
    arith_field.add_constraint(EvenConstraint::new(0));

    println!(
        "Arithmetic field constraints: {}",
        arith_field.describe_constraints()
    );
    println!(
        "Segment allowed? {}",
        arith_field.allows(&arith_segment.coordinates())
    );

    if let Some(val) = observe(&arith_field, &arith_segment, &IntegerProjector::new(0)) {
        println!("Observed value: {}", val);
    }

    let next_arith = possible_next_coordinates(&arith_field, &arith_segment);
    println!(
        "Possible next values (filtered by even constraint): {:?}",
        next_arith.iter().map(|c| c.raw[0]).collect::<Vec<_>>()
    );
    println!();

    // 7. Demonstrate that projections are ephemeral – we don't store them.
    println!("Projections are ephemeral: they are returned but not cached by the core.");
    println!("If you need a projection again, you must observe again.");
    println!();

    // 8. Show that time is just another coordinate (conceptual)
    println!("Time is just another coordinate. To model a temporal sequence,");
    println!("include a time axis in your coordinates and compare values on that axis.");
    println!("For example, coordinates [t, x, y] with t as time.");
    println!();

    println!("SSCCS PoC rewrite complete – aligned with constitutional principles.");
}
