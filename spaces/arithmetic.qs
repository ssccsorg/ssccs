// arithmetic.qs - 개선된 산술 상태 공간

use crate::{ConstrainableStateSpace, SpaceCoordinates, StateSpace};
use std::collections::HashSet;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ArithmeticConstraint {
    InRange(i64, i64),
    MultipleOf(i64),
    Even,
    Positive,
}

pub type ArithmeticSpace = ConstrainableStateSpace<ArithmeticConstraint>;

impl StateSpace for ArithmeticSpace {
    fn coordinates(&self) -> SpaceCoordinates {
        self.coordinates.clone()
    }

    fn constraint(&self) -> bool {
        // 좌표를 정수로 해석 (첫 번째 원소)
        let value = if let Some(first) = self.coordinates.raw.first() {
            *first
        } else {
            return false;
        };

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

    fn transitions(&self) -> Vec<Self> {
        if !self.constraint() {
            return Vec::new();
        }

        // 좌표를 정수로 해석 (첫 번째 원소)
        let x = if let Some(first) = self.coordinates.raw.first() {
            *first
        } else {
            return Vec::new();
        };

        let mut transitions = Vec::new();

        // 덧셈 (+1, +2)
        transitions.push(
            ArithmeticSpace::new(SpaceCoordinates::new(vec![x + 1]))
                .with_constraints(self.constraints.clone()),
        );
        transitions.push(
            ArithmeticSpace::new(SpaceCoordinates::new(vec![x + 2]))
                .with_constraints(self.constraints.clone()),
        );

        // 곱셈 (*2)
        transitions.push(
            ArithmeticSpace::new(SpaceCoordinates::new(vec![x * 2]))
                .with_constraints(self.constraints.clone()),
        );

        // 뺄셈 (-1)
        if x > 0 {
            transitions.push(
                ArithmeticSpace::new(SpaceCoordinates::new(vec![x - 1]))
                    .with_constraints(self.constraints.clone()),
            );
        }

        // 나눗셈 (/2) - 정수 나눗셈만
        if x != 0 && x.abs() >= 2 {
            let div = if x > 0 { x / 2 } else { x / 2 - 1 };
            transitions.push(
                ArithmeticSpace::new(SpaceCoordinates::new(vec![div]))
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
