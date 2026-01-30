//! Quasar State-Space Computing Core

use std::collections::HashSet;
use std::fmt::Debug;

/// State space: structure with all possible paths
pub trait StateSpace: Clone + Debug {
    type Value: Eq + std::hash::Hash + Copy;

    fn value(&self) -> Self::Value;
    fn constraint(&self) -> bool;
    fn transitions(&self) -> Vec<Self>;

    fn generate_tree(&self, max_states: usize) -> Vec<Self> {
        use std::collections::HashSet;
        let mut result = Vec::new();
        let mut stack = vec![self.clone()];
        let mut visited = HashSet::new(); // For cycle prevention

        while let Some(state) = stack.pop() {
            let val = state.value();
            // Skip already visited values ​​(avoid cycles)
            if visited.contains(&val) {
                continue;
            }
            visited.insert(val);
            result.push(state.clone());
            if result.len() >= max_states {
                break;
            }
            // Push in reverse order to ensure stack order
            let mut next_states = state.transitions();
            next_states.reverse();
            for next in next_states {
                if next.constraint() && !visited.contains(&next.value()) {
                    stack.push(next);
                }
            }
        }
        result
    }
}

mod branching {
    include!("../spaces/branching.qs");
}
pub use branching::{ Branching, create_branching };

/// Observation: Find a set of states in state space that satisfies a condition.
pub fn observe<S: StateSpace>(states: &[S], target: S::Value) -> HashSet<S::Value> {
    let mut results = HashSet::new();
    for state in states {
        if state.value() == target && state.constraint() {
            for next in state.transitions() {
                if next.constraint() {
                    results.insert(next.value());
                }
            }
        }
    }
    results
}

/// Projection: Interpret collapsed results from various perspectives
/// IMPORTANT: Add `Debug` bound (to output trait object)
pub trait Projection<T: Eq + std::hash::Hash + Copy>: Debug {
    fn project(&self, values: &HashSet<T>) -> HashSet<String>;
}

#[derive(Debug)] // Already implemented
pub struct NextValues;
#[derive(Debug)] // Already implemented
pub struct GrowthType;
#[derive(Debug)] // Already implemented
pub struct Magnitude;

impl Projection<i64> for NextValues {
    fn project(&self, values: &HashSet<i64>) -> HashSet<String> {
        values
            .iter()
            .map(|&x| format!("Next: {}", x + 1))
            .collect()
    }
}

impl Projection<i64> for GrowthType {
    fn project(&self, values: &HashSet<i64>) -> HashSet<String> {
        values
            .iter()
            .map(|&x| if x % 2 == 0 { "even".to_string() } else { "odd".to_string() })
            .collect()
    }
}

impl Projection<i64> for Magnitude {
    fn project(&self, values: &HashSet<i64>) -> HashSet<String> {
        values
            .iter()
            .map(|&x| if x > 5 { "large".to_string() } else { "small".to_string() })
            .collect()
    }
}
