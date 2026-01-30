// boolean.qs - 논리 상태 공간

use crate::{ConstrainableStateSpace, StateSpace};

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum BooleanConstraint {
    MustBeTrue,
    MustBeFalse,
}

pub type BooleanSpace = ConstrainableStateSpace<bool, BooleanConstraint>;

impl StateSpace for BooleanSpace {
    type Value = bool;

    fn value(&self) -> bool {
        self.value
    }

    fn constraint(&self) -> bool {
        for constraint in &self.constraints {
            match constraint {
                BooleanConstraint::MustBeTrue => {
                    if !self.value {
                        return false;
                    }
                }
                BooleanConstraint::MustBeFalse => {
                    if self.value {
                        return false;
                    }
                }
            }
        }
        true
    }

    fn transitions(&self) -> Vec<Self> {
        if !self.constraint() {
            return Vec::new();
        }

        // 논리 연산 전이: NOT, AND(true), OR(false)
        let mut transitions = Vec::new();

        // NOT 연산
        transitions.push(BooleanSpace::new(!self.value).with_constraints(self.constraints.clone()));

        // AND true (값이 true일 때만)
        if self.value {
            transitions.push(BooleanSpace::new(true).with_constraints(self.constraints.clone()));
        }

        // OR false (값이 false일 때만)
        if !self.value {
            transitions.push(BooleanSpace::new(false).with_constraints(self.constraints.clone()));
        }

        transitions
    }
}

impl BooleanSpace {
    pub fn create(value: bool) -> Self {
        Self::new(value)
    }

    pub fn create_true() -> Self {
        Self::new(true).with_constraint(BooleanConstraint::MustBeTrue)
    }

    pub fn create_false() -> Self {
        Self::new(false).with_constraint(BooleanConstraint::MustBeFalse)
    }
}
