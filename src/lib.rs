//! Quasar State-Space Computing Core

mod constrainable;
// space_factory는 일단 제외 - 필요시 추가

pub use constrainable::*;

use std::collections::HashSet;
use std::fmt::Debug;

/// 상태 공간: 가능한 모든 경로를 가진 구조 (원시 정의)
pub trait StateSpace: Clone + PartialEq + Eq + std::hash::Hash {
    type Value: Eq + std::hash::Hash + Copy;

    fn value(&self) -> Self::Value;
    fn constraint(&self) -> bool;
    fn transitions(&self) -> Vec<Self>;

    fn generate_tree(&self, max_states: usize) -> HashSet<Self> {
        let mut visited = HashSet::new();
        let mut result = HashSet::new();
        let mut stack = vec![self.clone()];

        while let Some(state) = stack.pop() {
            if !visited.insert(state.clone()) {
                continue;
            }

            result.insert(state.clone());

            if result.len() >= max_states {
                break;
            }

            for next in state.transitions() {
                if next.constraint() && !visited.contains(&next) {
                    stack.push(next);
                }
            }
        }

        result
    }
}

/// 관찰 함수
pub fn observe<S: StateSpace>(states: &HashSet<S>, target: S::Value) -> HashSet<S::Value> {
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

/// 프로젝션 계층
pub trait Projection<T: Eq + std::hash::Hash + Copy>: Debug {
    fn project(&self, values: &HashSet<T>) -> HashSet<String>;
}

#[derive(Debug)]
pub struct NextValues;
#[derive(Debug)]
pub struct OperationType;
#[derive(Debug)]
pub struct Magnitude;

impl Projection<i64> for NextValues {
    fn project(&self, values: &HashSet<i64>) -> HashSet<String> {
        values.iter().map(|&x| format!("Next: {}", x + 1)).collect()
    }
}

impl Projection<i64> for OperationType {
    fn project(&self, values: &HashSet<i64>) -> HashSet<String> {
        values
            .iter()
            .map(|&x| {
                if x % 2 == 0 {
                    "even".to_string()
                } else {
                    "odd".to_string()
                }
            })
            .collect()
    }
}

impl Projection<i64> for Magnitude {
    fn project(&self, values: &HashSet<i64>) -> HashSet<String> {
        values
            .iter()
            .map(|&x| {
                if x > 5 {
                    "large".to_string()
                } else {
                    "small".to_string()
                }
            })
            .collect()
    }
}

/// .qs 파일 포함
mod arithmetic {
    include!("../spaces/arithmetic.qs");
}
pub use arithmetic::*;
