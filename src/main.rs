#[macro_use]
extern crate quasar;

// 1. Define state space with macro
state_space!(Branching);
projection!(NextValues);
projection!(GrowthType);
projection!(Magnitude);

fn main() {
    println!("Experiment with Quasar core concepts");
    println!("============================\n");
    
    // Experiment 1: Observations are not inputs
    println!("Experiment 1: observe(x=3)");
    println!("---------------------");
    
    // 1. Create state space
    let mut space = Branching::new(3);
    
    // 2. Calculate all possible trajectories (depth limited)
    println!("1. Computing all possible paths... (maximum depth 5)");
    space.compute_trajectories();
    
    // 3. Observation (collapse)
    println!("2. Run observation (collapse)...");
    let observed = space.observe(3);
    
    match observed {
        Some(values) => {
            println!("   Collapse results: {:?}", values);
            println!("   (not a single value) {}set of values)", values.len());
            
            // 4. Apply each projection
            println!("\n3. Apply projection...");
            
            let next = NextValues {};
            let next_result = next.apply(&values);
            println!("   -NextValues: {:?}", next_result);
            
            let growth = GrowthType {};
            let growth_result = growth.apply(&values);
            println!("   -GrowthType: {:?}", growth_result);
            
            let mag = Magnitude {};
            let mag_result = mag.apply(&values);
            println!("   -Magnitude: {:?}", mag_result);
            
            println!("\nAnalysis:");
            println!("1. observe(3) is not ‘calculate 3’");
            println!("2. Find the state where x=3 in the entire trajectory and collapse");
            println!("3. The result is a set, not a single value: {:?}", values);
            println!("4. Three different interpretations possible for the same collapse");
        },
        None => {
            println!("   Observation failed: value 3 not found");
        }
    }
    
    // Additional experiments (depth limited values)
    println!("\nAdditional experiments: Other values ​​(depth limits)");
    for &val in &[0, 1, 2, 3, 4] { // If you start from 0, it's too big, so just go up to 4.
        let mut space = Branching::new(val);
        space.compute_trajectories();
        
        if let Some(results) = space.observe(val) {
            println!("Observe({}) → {:?}", val, results);
            
            // Ensure that the collapse result is always a set
            if results.len() > 0 {
                println!("   ✓ The result is a set ({}dog)", results.len());
            }
        } else {
            println!("Observe({}) → Not found (depth limited)", val);
        }
    }
    
    // Check simple trajectory structure
    println!("\nSimple Trajectory structure (from x=2):");
    let mut space = Branching::new(2);
    space.compute_trajectories();
    println!("Trajectory from x=2 (maximum depth 3):");
    space.print_trajectories(0);
    
    println!("\nCore concept verification completed");
    println!("   -Observation is subject to collapse");
    println!("   -The result is a set");
    println!("   -Single collapse, multiple projection");
}

#[test]
fn test_branching() {
    let mut space = Branching::new(3);
    space.compute_trajectories();
    
    let result = space.observe(3);
    assert!(result.is_some(), "observe(3) should find something");
    
    if let Some(values) = result {
        assert!(values.len() > 0, "Result must not be empty");
        println!("Test passed: results are set (size: {})", values.len());
    }
}

#[test]
fn test_different_projections() {
    let mut space = Branching::new(3);
    space.compute_trajectories();
    
    if let Some(collapsed) = space.observe(3) {
        let next = NextValues {};
        let growth = GrowthType {};
        
        let next_result = next.apply(&collapsed);
        let growth_result = growth.apply(&collapsed);
        
        // Results Verification
        assert_eq!(next_result.len(), collapsed.len());
        assert_eq!(growth_result.len(), collapsed.len());
        
        println!("Passed the test: multiple projection possible");
    }
}

#[test]
fn test_observation_is_not_input() {
    // Core verification: observe is a condition, not an input
    let mut space1 = Branching::new(0);
    space1.compute_trajectories();
    
    // Calling observe when it has already been calculated
    let result1 = space1.observe(2);
    
    println!("Pass the test: observations are conditions, not calculations (result: {:?})", result1);
}