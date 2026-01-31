// boolean.ss - 논리 상태 공간

use crate::{ConstrainableStateSpace, ConstraintSet, SpaceCoordinates, StateSpace};
use std::collections::HashSet;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum BooleanConstraint {
    MustBeTrue,
    MustBeFalse,
}

pub type BooleanSpace = ConstrainableStateSpace<BooleanConstraint>;

impl BooleanSpace {
    /// 특정 불리언 값이 모든 제약조건을 만족하는지 확인
    fn satisfies_constraints(&self, value: bool) -> bool {
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
}

impl StateSpace for BooleanSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coordinates.clone()
    }

    fn constraint_set(&self) -> ConstraintSet {
        // 좌표를 불리언으로 해석
        let value = if let Some(first) = self.coordinates.raw.first() {
            *first != 0
        } else {
            return ConstraintSet::empty();
        };

        let mut allowed = HashSet::new();

        // 현재 값이 제약조건을 만족하면 추가
        if self.satisfies_constraints(value) {
            allowed.insert(SpaceCoordinates::new(vec![if value { 1 } else { 0 }]));
        }

        // 반대 값도 검토
        let opposite_value = !value;
        if self.satisfies_constraints(opposite_value) {
            allowed.insert(SpaceCoordinates::new(vec![if opposite_value {
                1
            } else {
                0
            }]));
        }

        ConstraintSet::new(allowed)
    }

    fn possible_transitions(&self) -> HashSet<Self> {
        // Vec → HashSet
        // 현재 좌표를 불리언으로 해석
        let value = if let Some(first) = self.coordinates.raw.first() {
            *first != 0
        } else {
            return HashSet::new();
        };

        let mut transitions = HashSet::new();

        // NOT 연산
        transitions.insert(
            // push → insert
            BooleanSpace::new(SpaceCoordinates::new(vec![if value { 0 } else { 1 }]))
                .with_constraints(self.constraints.clone()),
        );

        // 현재 값 복사
        transitions.insert(
            // push → insert
            BooleanSpace::new(SpaceCoordinates::new(vec![if value { 1 } else { 0 }]))
                .with_constraints(self.constraints.clone()),
        );

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
