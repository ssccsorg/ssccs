// branching.qs -Quasar State Space Definition
// Essentials of a .qs file: a valid Rust code (extension to indicate logical boundaries)

use super::StateSpace; // Import traits from parent module

/// branch state space
#[derive(Clone, Debug)]
pub struct Branching {
    pub x: i64,
}

impl StateSpace for Branching {
    type Value = i64;

    fn value(&self) -> i64 {
        self.x
    }

    fn constraint(&self) -> bool {
        self.x >= 0 && self.x <= 10
    }

    fn transitions(&self) -> Vec<Self> {
        vec![Branching { x: self.x + 1 }, Branching { x: self.x * 2 }]
    }
}

pub fn create_branching(value: i64) -> Branching {
    Branching { x: value }
}
