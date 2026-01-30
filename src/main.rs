use quasar::{observe, NextValues, GrowthType, Magnitude, Projection, create_branching, StateSpace};

fn main() {
    println!(" Quasar PoC -Validation of Core Concepts");
    println!("===============================\n");
    
    let root = create_branching(0);
    let all_states = root.generate_tree(100);
    
    println!("1. Create state space (tree structure):");
    println!("   gun {}Dog status created", all_states.len());
    println!("   (all possible paths already exist)\n");
    
    println!("2. Observation experiment: observe(x=3)");
    println!("   -----------------------");
    let observed = observe(&all_states, 3);
    println!("   result: {:?}", observed);
    println!("   size: {} (Set!)\n", observed.len());
    
    println!("3. Mapper vs Quasar comparison:");
    println!("   Mapper: f(3) → single value");
    println!("   Quasar: observe(3) → set {:?}\n", observed);
    assert!(observed.len() > 1, "The result should be a set, not a single value");
    println!("   Verification passed: the result is a set\n");
    
    println!("4. Multiple projection:");
    println!("   -----------------");
    let projections: Vec<Box<dyn Projection<i64>>> = vec![
        Box::new(NextValues),
        Box::new(GrowthType),
        Box::new(Magnitude),
    ];
    for proj in projections {
        let result = proj.project(&observed);
        // Now output is possible as {:?} (solved by adding Debug bound)
        println!("   - {:?}: {:?}", proj, result);
    }
    println!();
    
    println!(" PoC verification completed!");
    println!("Key concepts:");
    println!("- .qs = 100% Rust code (marking logical boundaries)");
    println!("- Observation = Find a set of states that satisfy a condition (not a single value)");
    println!("- Single collapse → multiple projection");
}

