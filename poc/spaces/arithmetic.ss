// arithmetic.ss - 개선된 산술 상태 공간

use crate::{ConstrainableStateSpace, ConstraintSet, SpaceCoordinates, StateSpace};
use std::collections::HashSet;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ArithmeticConstraint {
    InRange(i64, i64),
    MultipleOf(i64),
    Even,
    Positive,
}

pub type ArithmeticSpace = ConstrainableStateSpace<ArithmeticConstraint>;

impl ArithmeticSpace {
    /// 특정 값이 모든 제약조건을 만족하는지 확인
    fn satisfies_constraints(&self, value: i64) -> bool {
        for constraint in &self.constraints {
            match constraint {
                ArithmeticConstraint::InRange(min, max) => {
                    if value < *min || value > *max {
                        return false;
                    }
                }
                ArithmeticConstraint::MultipleOf(n) => {
                    if *n == 0 || value % n != 0 {
                        return false;
                    }
                }
                ArithmeticConstraint::Even => {
                    if value % 2 != 0 {
                        return false;
                    }
                }
                ArithmeticConstraint::Positive => {
                    if value <= 0 {
                        return false;
                    }
                }
            }
        }
        true
    }

    /// 제약조건을 고려한 가능한 다음 값들 생성
    fn possible_next_values(&self, current_value: i64) -> Vec<i64> {
        let mut values = Vec::new();

        // 덧셈 (+1, +2)
        values.push(current_value + 1);
        values.push(current_value + 2);

        // 곱셈 (*2)
        values.push(current_value * 2);

        // 뺄셈 (-1)
        if current_value > 0 {
            values.push(current_value - 1);
        }

        // 나눗셈 (/2) - 정수 나눗셈만
        if current_value != 0 && current_value.abs() >= 2 {
            let div = if current_value > 0 {
                current_value / 2
            } else {
                current_value / 2 - 1
            };
            values.push(div);
        }

        values
    }
}

impl StateSpace for ArithmeticSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coordinates.clone()
    }

    fn constraint_set(&self) -> ConstraintSet {
        // 현재 좌표 값 추출
        let current_value = if let Some(first) = self.coordinates.raw.first() {
            *first
        } else {
            return ConstraintSet::empty();
        };

        let mut allowed = HashSet::new();

        // 현재 값이 제약조건을 만족하면 추가
        if self.satisfies_constraints(current_value) {
            allowed.insert(SpaceCoordinates::new(vec![current_value]));
        }

        // 간단한 PoC: 가능한 다음 값들 중 제약조건을 만족하는 것들만 추가
        for next_value in self.possible_next_values(current_value) {
            if self.satisfies_constraints(next_value) {
                allowed.insert(SpaceCoordinates::new(vec![next_value]));
            }
        }

        ConstraintSet::new(allowed)
    }

    fn possible_transitions(&self) -> HashSet<Self> {
        // Vec → HashSet
        // 현재 좌표 값 추출
        let current_value = if let Some(first) = self.coordinates.raw.first() {
            *first
        } else {
            return HashSet::new();
        };

        let mut transitions = HashSet::new();

        // 가능한 모든 다음 값들에 대해 상태 생성
        for next_value in self.possible_next_values(current_value) {
            transitions.insert(
                // push → insert
                ArithmeticSpace::new(SpaceCoordinates::new(vec![next_value]))
                    .with_constraints(self.constraints.clone()),
            );
        }

        transitions
    }
}

impl ArithmeticSpace {
    pub fn create(value: i64) -> Self {
        Self::new(SpaceCoordinates::new(vec![value]))
    }

    pub fn create_in_range(value: i64, min: i64, max: i64) -> Self {
        Self::new(SpaceCoordinates::new(vec![value]))
            .with_constraint(ArithmeticConstraint::InRange(min, max))
    }

    pub fn create_even(value: i64) -> Self {
        Self::new(SpaceCoordinates::new(vec![value])).with_constraint(ArithmeticConstraint::Even)
    }

    pub fn create_positive(value: i64) -> Self {
        Self::new(SpaceCoordinates::new(vec![value]))
            .with_constraint(ArithmeticConstraint::Positive)
    }

    pub fn create_with_constraints(value: i64, constraints: HashSet<ArithmeticConstraint>) -> Self {
        Self::new(SpaceCoordinates::new(vec![value])).with_constraints(constraints)
    }
}
