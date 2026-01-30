// boolean.qs - 논리 상태 공간

use crate::{ConstrainableStateSpace, SpaceCoordinates, StateSpace};

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum BooleanConstraint {
    MustBeTrue,
    MustBeFalse,
}

pub type BooleanSpace = ConstrainableStateSpace<BooleanConstraint>;

impl StateSpace for BooleanSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coordinates.clone()
    }

    fn constraint(&self) -> bool {
        // 좌표를 불리언으로 해석 (첫 번째 원소: 0 -> false, 1 -> true)
        let value = if let Some(first) = self.coordinates.raw.first() {
            *first != 0
        } else {
            return false;
        };

        for constraint in &self.constraints {
            match constraint {
                BooleanConstraint::MustBeTrue => {
                    if !value {
                        return false;
                    }
                }
                BooleanConstraint::MustBeFalse => {
                    if value {
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

        // 좌표를 불리언으로 해석
        let value = if let Some(first) = self.coordinates.raw.first() {
            *first != 0
        } else {
            return Vec::new();
        };

        let mut transitions = Vec::new();

        // NOT 연산
        transitions.push(
            BooleanSpace::new(SpaceCoordinates::new(vec![if value { 0 } else { 1 }]))
                .with_constraints(self.constraints.clone()),
        );

        // AND true (값이 true일 때만)
        if value {
            transitions.push(
                BooleanSpace::new(SpaceCoordinates::new(vec![1]))
                    .with_constraints(self.constraints.clone()),
            );
        }

        // OR false (값이 false일 때만)
        if !value {
            transitions.push(
                BooleanSpace::new(SpaceCoordinates::new(vec![0]))
                    .with_constraints(self.constraints.clone()),
            );
        }

        transitions
    }
}

impl BooleanSpace {
    pub fn create(value: bool) -> Self {
        Self::new(SpaceCoordinates::new(vec![if value { 1 } else { 0 }]))
    }

    pub fn create_true() -> Self {
        Self::new(SpaceCoordinates::new(vec![1])).with_constraint(BooleanConstraint::MustBeTrue)
    }

    pub fn create_false() -> Self {
        Self::new(SpaceCoordinates::new(vec![0])).with_constraint(BooleanConstraint::MustBeFalse)
    }
}
