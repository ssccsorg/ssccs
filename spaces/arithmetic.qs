// arithmetic.qs - 개선된 산술 상태 공간

use crate::{ConstrainableStateSpace, StateSpace};
use std::collections::HashSet;

#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ArithmeticConstraint {
    InRange(i64, i64),
    MultipleOf(i64),
    Even,
    Positive,
    // Negative 제거 (충돌 가능성)
}

pub type ArithmeticSpace = ConstrainableStateSpace<i64, ArithmeticConstraint>;

impl StateSpace for ArithmeticSpace {
    type Value = i64;

    fn value(&self) -> i64 {
        self.value
    }

    fn constraint(&self) -> bool {
        for constraint in &self.constraints {
            match constraint {
                ArithmeticConstraint::InRange(min, max) => {
                    if self.value < *min || self.value > *max {
                        return false;
                    }
                }
                ArithmeticConstraint::MultipleOf(n) => {
                    if *n == 0 || self.value % n != 0 {
                        return false;
                    }
                }
                ArithmeticConstraint::Even => {
                    if self.value % 2 != 0 {
                        return false;
                    }
                }
                ArithmeticConstraint::Positive => {
                    if self.value <= 0 {
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

        let x = self.value;
        let mut transitions = Vec::new();

        // (generate_tree에서 constraint()로 필터링하므로 여기서는 모든 가능성 생성)

        // 덧셈 (+1, +2)
        transitions.push(ArithmeticSpace::new(x + 1).with_constraints(self.constraints.clone()));
        transitions.push(ArithmeticSpace::new(x + 2).with_constraints(self.constraints.clone()));

        // 곱셈 (*2)
        transitions.push(ArithmeticSpace::new(x * 2).with_constraints(self.constraints.clone()));

        // 뺄셈 (-1)
        if x > 0 {
            // 음수 방지 (Positive 제약과의 충돌 회피)
            transitions
                .push(ArithmeticSpace::new(x - 1).with_constraints(self.constraints.clone()));
        }

        // 나눗셈 (/2) - 정수 나눗셈만
        if x != 0 && x.abs() >= 2 {
            let div = if x > 0 { x / 2 } else { x / 2 - 1 }; // Rust 정수 나눗셈 보정
            transitions.push(ArithmeticSpace::new(div).with_constraints(self.constraints.clone()));
        }

        transitions
    }
}

impl ArithmeticSpace {
    pub fn create(value: i64) -> Self {
        Self::new(value)
    }

    pub fn create_in_range(value: i64, min: i64, max: i64) -> Self {
        Self::new(value).with_constraint(ArithmeticConstraint::InRange(min, max))
    }

    pub fn create_even(value: i64) -> Self {
        Self::new(value).with_constraint(ArithmeticConstraint::Even)
    }

    pub fn create_positive(value: i64) -> Self {
        Self::new(value).with_constraint(ArithmeticConstraint::Positive)
    }

    pub fn create_with_constraints(value: i64, constraints: HashSet<ArithmeticConstraint>) -> Self {
        Self::new(value).with_constraints(constraints)
    }
}
