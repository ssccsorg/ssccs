use quasar::{
    ArithmeticConstraint, ArithmeticSpace, Magnitude, NextValues, OperationType, Projection,
    StateSpace, observe,
};
use std::collections::HashSet;

fn main() {
    println!("Quasar PoC");
    println!("===============================\n");

    // Relax Constraints: Expand Scope + Start with a Single Constraint
    println!("1. Create state space (relaxed constraints):");
    let space1 = ArithmeticSpace::create_in_range(5, 0, 30); // range extension
    let space2 = ArithmeticSpace::create_even(4); // single constraint
    let space3 = ArithmeticSpace::create_positive(3); // single constraint

    println!("   Space1 (0~30): {:?}", space1);
    println!("   Space2 (Even): {:?}", space2);
    println!("   Space3 (Positive): {:?}\n", space3);

    // Reasonable combination of constraints
    println!("2. Rational combination of constraints:");
    let mut constraints = HashSet::new();
    constraints.insert(ArithmeticConstraint::InRange(0, 25)); // plenty of room to grow
    constraints.insert(ArithmeticConstraint::Positive); // Basic safety constraints
    // Even constraint removed: odd numbers may occur during transition

    let constrained = ArithmeticSpace::create_with_constraints(5, constraints);
    println!("   Constrained space: {:?}\n", constrained);

    // Tree creation (20 states)
    println!("3. Create state tree:");
    let tree = constrained.generate_tree(20);
    println!("   Tree Size: {}", tree.len());

    // Debug: Print generated status values
    let values: Vec<i64> = tree.iter().map(|s| s.value()).collect();
    println!("   Status values: {:?}\n", values);

    // Observation (now a valid transition)
    println!("4. Observation experiment:");
    let observed = observe(&tree, 5);
    println!("   observe(5) = {:?}", observed);
    println!("   Set size: {} (always >0)\n", observed.len());
    assert!(observed.len() > 0, "Observations must not be empty");

    // multiple projection
    println!("5. Multiple projection:");
    let projections: Vec<Box<dyn Projection<i64>>> = vec![
        Box::new(NextValues),
        Box::new(OperationType),
        Box::new(Magnitude),
    ];

    for proj in projections {
        let result = proj.project(&observed);
        println!("   - {:?}: {:?}", proj, result);
    }
    println!();

    println!(" PoC verification completed!");
    println!("\nKey Lesson:");
    println!("• Constraints must ensure ‘growth potential’.");
    println!(
        "• Transition rules do not apply constraints immediately but are filtered after creation."
    );
    println!("• State space is a mathematical set: exists in parallel without order.");
}
