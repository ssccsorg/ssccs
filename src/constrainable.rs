//! Constrainable State Space Extension
//! 제약조건을 가진 상태 공간의 기본 구현

use std::collections::HashSet;
use std::fmt::{Debug, Formatter};
use std::hash::{Hash, Hasher};

/// 제약조건을 가진 상태 공간 (단순화된 구현)
#[derive(Clone)]
pub struct ConstrainableStateSpace<V, C>
where
    V: Eq + std::hash::Hash + Copy,
    C: Eq + std::hash::Hash + Clone,
{
    /// 상태 값
    pub value: V,

    /// 제약조건 집합 (순서 없음)
    pub constraints: HashSet<C>,
}

// 수동으로 PartialEq 구현
impl<V, C> PartialEq for ConstrainableStateSpace<V, C>
where
    V: Eq + std::hash::Hash + Copy,
    C: Eq + std::hash::Hash + Clone,
{
    fn eq(&self, other: &Self) -> bool {
        self.value == other.value && self.constraints == other.constraints
    }
}

impl<V, C> Eq for ConstrainableStateSpace<V, C>
where
    V: Eq + std::hash::Hash + Copy,
    C: Eq + std::hash::Hash + Clone,
{
}

// 수동으로 Hash 구현
impl<V, C> Hash for ConstrainableStateSpace<V, C>
where
    V: Eq + std::hash::Hash + Copy,
    C: Eq + std::hash::Hash + Clone,
{
    fn hash<H: Hasher>(&self, state: &mut H) {
        self.value.hash(state);
        // HashSet의 해시는 순서에 의존하지 않음
        for constraint in &self.constraints {
            constraint.hash(state);
        }
    }
}

impl<V, C> ConstrainableStateSpace<V, C>
where
    V: Eq + std::hash::Hash + Copy,
    C: Eq + std::hash::Hash + Clone,
{
    /// 새 상태 공간 생성 (기본 제약조건 없음)
    pub fn new(value: V) -> Self {
        Self {
            value,
            constraints: HashSet::new(),
        }
    }

    /// 제약조건 추가 (불변 연산)
    pub fn with_constraint(self, constraint: C) -> Self {
        let mut new_constraints = self.constraints.clone();
        new_constraints.insert(constraint);

        Self {
            value: self.value,
            constraints: new_constraints,
        }
    }

    /// 제약조건들 추가
    pub fn with_constraints<I>(self, constraints: I) -> Self
    where
        I: IntoIterator<Item = C>,
    {
        let mut new_constraints = self.constraints.clone();
        new_constraints.extend(constraints);

        Self {
            value: self.value,
            constraints: new_constraints,
        }
    }
}

impl<V, C> Debug for ConstrainableStateSpace<V, C>
where
    V: Eq + std::hash::Hash + Copy + Debug,
    C: Eq + std::hash::Hash + Clone + Debug,
{
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        write!(
            f,
            "ConstrainableStateSpace({:?}, constraints: {:?})",
            self.value, self.constraints
        )
    }
}
