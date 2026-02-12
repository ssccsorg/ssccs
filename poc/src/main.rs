use ssccs_poc::arithmetic::ArithmeticSpace;
use ssccs_poc::basic::BasicSpace;
use ssccs_poc::fields::FieldBuilder;
use ssccs_poc::spaces::*;
use ssccs_poc::*;

fn main() {
    println!(" Scheme SegmentScheme-Segment Computing (StateField 버전)");
    println!("==================================================\n");

    // 1. Basic structural experiment
    println!(" 1. Basic structural experiment:");
    let coords = SpaceCoordinates::new(vec![1, 2, 3]);
    println!("   Pure coordinates: {:?}", coords.raw);
    println!("   Coordinates are meaningless: just an array of numbers");
    println!();

    // 2. Create state space
    println!(" 2. Create state space:");
    let basic_space = basic::BasicSpace::new(coords.clone());
    println!(
        "   BasicSpace coordinates: {:?}",
        basic_space.coordinates().raw
    );

    // Wrap it with StateField
    let basic_field: StateField<BasicSpace, i64, i64> =
        fields::FieldBuilder::<BasicSpace, i64, i64>::new(basic_space.clone())
            .add_constraint(RangeConstraint::new(0, 0, 10))
            .add_constraint(RangeConstraint::new(1, 0, 5))
            .build();

    println!(
        "   StateField constraints: {}",
        basic_field.constraints.describe()
    );
    println!("   Allowed: {}", basic_field.is_allowed());
    println!();

    // 3. Add constraints
    println!(" 3. Add constraints:");
    let constrained_field: StateField<BasicSpace, i64, i64> =
        FieldBuilder::new(basic::BasicSpace::new(coords.clone()))
            .add_constraint(RangeConstraint::new(0, 0, 10))
            .add_constraint(RangeConstraint::new(1, 0, 5))
            .build();

    println!(
        "   Constraints: {}",
        constrained_field.constraints.describe()
    );
    println!(
        "   Coordinates [1,2,3] allowed: {}",
        constrained_field.is_allowed()
    );
    println!("   Constraints are structural limitations of space");
    println!();

    // 4. Projection experiment
    println!(" 4. Projection experiment:");
    let projector = IntegerProjector::new(0);
    let projection = projector.project(&coords);
    println!("   Projector: Extract first axis values");
    println!("   Projection result: {:?}", projection);
    println!("   Same coordinates → different projectors → different meanings");
    println!();

    // 5. Arithmetic space experiment
    println!(" 5. Arithmetic space experiment:");
    let arithmetic_space = arithmetic::ArithmeticSpace::new(5);
    println!(
        "   Arithmetic space coordinates: {:?}",
        arithmetic_space.coordinates().raw
    );
    println!("   Arithmetic adjacency: +1, -1, ×2, ×², etc.");

    let arithmetic_field: StateField<ArithmeticSpace, i64, i64> =
        FieldBuilder::new(arithmetic_space.clone())
            .add_constraint(RangeConstraint::new(0, 0, 50))
            .build();

    let direct = observe_field(&arithmetic_field, &projector);
    println!("   Direct observation: {:?}", direct);

    // Adjacent observations (possible transitions)
    let possible_transitions = arithmetic_field.possible_transitions();
    println!("   Possible transitions: {}dog", possible_transitions.len());
    println!(
        "   Transition example: {:?}",
        possible_transitions
            .iter()
            .take(3)
            .map(|s| s.coordinates().raw[0])
            .collect::<Vec<_>>()
    );
    println!();

    // 6. Tree navigation
    println!(" 6. Tree navigation:");
    let tree_results = observe_tree(&arithmetic_field, &projector, 2);
    println!("   Depth 2 search results: {:?}", tree_results);
    println!("   Searched values: {}dog", tree_results.len());
    println!();

    // 7. Observer pattern
    println!(" 7. Observer pattern:");
    let observer = ValueObserver::new(5, "Check if value is 5");

    // Current value observation
    let current_value = projector.project(&arithmetic_field.space.coordinates());
    if let Some(value) = current_value {
        println!("   Current value: {}", value);
        println!("   Observations: {}", observer.observe(&value));
        println!("   Observation Description: {}", observer.describe());
    }

    // Transposed value observation
    if let Some(first_transition) = possible_transitions.first() {
        let transition_value = projector.project(&first_transition.coordinates());
        if let Some(value) = transition_value {
            println!("   Transition value: {}", value);
            println!("   Observations: {}", observer.observe(&value));
        }
    }
    println!("   Observation = Projection + Expected Value Comparison");
    println!();

    // 8. Synthesis experiments
    println!(" 8. Spatial compositing:");
    let space1_field: StateField<BasicSpace, i64, i64> =
        FieldBuilder::new(basic::BasicSpace::new(SpaceCoordinates::new(vec![1, 2])))
            .add_constraint(RangeConstraint::new(0, 0, 5))
            .build();

    let space2_field: StateField<BasicSpace, i64, i64> =
        FieldBuilder::new(basic::BasicSpace::new(SpaceCoordinates::new(vec![1, 2])))
            .add_constraint(RangeConstraint::new(0, 0, 3))
            .build();

    let composition = compose_fields(&space1_field, &space2_field);
    println!("   Synthetic results: {:?}", composition);
    println!("   Synthesis = Analysis of relationships between spaces");
    println!();

    // 9. Even Constraint Testing
    println!(" 9. Testing even constraints:");
    let even_space = arithmetic::ArithmeticSpace::new(6);
    let even_field: StateField<ArithmeticSpace, i64, i64> = FieldBuilder::new(even_space)
        .add_constraint(EvenConstraint::new(0))
        .add_constraint(RangeConstraint::new(0, 0, 20))
        .build();

    println!("   coordinate: {:?}", even_field.space.coordinates().raw);
    println!("   Constraints: {}", even_field.constraints.describe());
    println!("   Allowed: {}", even_field.is_allowed());

    let even_transitions = even_field.possible_transitions();
    println!(
        "   Possible transitions under the even constraint: {}dog",
        even_transitions.len()
    );
    println!(
        "   Transition values: {:?}",
        even_transitions
            .iter()
            .map(|s| s.coordinates().raw[0])
            .collect::<Vec<_>>()
    );
    println!();

    // philosophical summary
    println!(" Philosophical Hierarchy:");
    println!("• Coordinates have the structure: SpaceCoordinates([x, y, z])");
    println!("• SchemeSegment = Structure + Basic Adjacency");
    println!("• StateField = SchemeSegment + Dynamic Field (constraint, transition, observation)");
    println!("• Constraints are allowed: Constraint.allows(coords)");
    println!("• Projection is semantic emergence: Projector.project(coords)");
    println!("• Observation verifies meaning: Observer.observe(value)");
    println!();

    println!(" Scheme SegmentState is immutable, conditions are variable, meaning is emergent!");
}
