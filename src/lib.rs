//! Quasar State-Space Computing Core
//! 철학: StateSpace는 값을 "가지지" 않음, 값은 투영의 결과물

mod constrainable;
pub use constrainable::*;

use std::collections::HashSet;
use std::fmt::Debug;

/// 투명한 구조적 좌표 - 의미 해석 금지
/// SpaceCoordinates are opaque structural identifiers.
/// They must not be interpreted without a projection.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct SpaceCoordinates {
    /// 투명한 구조적 좌표. 이 수준에서는 의미적 해석이 금지됩니다.
    pub raw: Vec<i64>,
}

impl SpaceCoordinates {
    /// 새로운 투명 좌표 생성
    pub fn new(raw: Vec<i64>) -> Self {
        Self { raw }
    }

    /// 빈 좌표 (투영 대기 상태)
    pub fn pending() -> Self {
        Self { raw: Vec::new() }
    }

    /// 좌표가 투영 가능한지 여부 (원소가 1개 이상)
    pub fn is_projectable(&self) -> bool {
        !self.raw.is_empty()
    }
}

/// 상태 공간: 가능성의 공간 (값을 가지지 않음)
pub trait StateSpace: Clone + PartialEq + Eq + std::hash::Hash {
    /// 이 상태 공간의 투명한 "좌표" - 구조적 식별자
    fn coordinates(&self) -> SpaceCoordinates;

    /// 제약조건 만족 여부 (내부적 평가)
    fn constraint(&self) -> bool;

    /// 전이 가능한 상태 공간들
    fn transitions(&self) -> Vec<Self>;

    /// 상태 트리 생성
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

/// 투영자: StateSpace를 특정 값으로 투영
pub trait SpaceProjector: Debug {
    type Output: Eq + std::hash::Hash + Clone + Debug;

    /// 상태 공간을 특정 차원의 값으로 투영
    /// 실패 시 None 반환 (투영 불가능한 좌표)
    fn project<S: StateSpace>(&self, space: &S) -> Option<Self::Output>;

    /// 투영 대상 차원
    fn target_dimension(&self) -> ProjectionAxis;

    /// 좌표를 투영 가능한지 확인
    fn can_project(&self, coordinates: &SpaceCoordinates) -> bool;
}

/// 투영 축
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub enum ProjectionAxis {
    /// 정수 차원
    Integer,
    /// 불리언 차원
    Boolean,
    /// 문자열 차원
    String,
    /// 투영자 정의 차원
    Custom(String),
}

/// 관측자: 특정 투영 결과를 기대하는 투영자
#[derive(Debug)]
pub struct Observer<P: SpaceProjector> {
    projector: P,
    expected: P::Output,
}

impl<P: SpaceProjector> Observer<P> {
    pub fn new(projector: P, expected: P::Output) -> Self {
        Self {
            projector,
            expected,
        }
    }
}

impl<P: SpaceProjector> SpaceProjector for Observer<P> {
    type Output = bool;

    fn project<S: StateSpace>(&self, space: &S) -> Option<bool> {
        match self.projector.project(space) {
            Some(value) => Some(value == self.expected),
            None => None,
        }
    }

    fn target_dimension(&self) -> ProjectionAxis {
        self.projector.target_dimension()
    }

    fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
        self.projector.can_project(coordinates)
    }
}

/// 관측 함수: 투영자를 사용하여 상태 공간 관측
pub fn observe<S: StateSpace, P: SpaceProjector>(
    states: &HashSet<S>,
    projector: &P,
) -> HashSet<P::Output>
where
    P::Output: Eq + std::hash::Hash + Clone,
{
    let mut results = HashSet::new();

    for state in states {
        if state.constraint() {
            if let Some(value) = projector.project(state) {
                results.insert(value);
            }
        }
    }

    results
}

/// 조건부 관측 함수: 특정 조건을 만족하는 상태의 전이들을 관측
pub fn observe_transitions<S: StateSpace, P: SpaceProjector>(
    states: &HashSet<S>,
    condition: &Observer<P>,
) -> HashSet<<P as SpaceProjector>::Output>
where
    P: SpaceProjector,
    P::Output: Eq + std::hash::Hash + Clone + Debug,
{
    let mut results = HashSet::new();

    for state in states {
        if !state.constraint() {
            continue;
        }

        // 조건 관측자가 이 상태를 관측함
        if let Some(true) = condition.project(state) {
            // 이 상태의 전이들을 원래 투영자로 투영
            for next in state.transitions() {
                if next.constraint() {
                    if let Some(value) = condition.projector.project(&next) {
                        results.insert(value);
                    }
                }
            }
        }
    }

    results
}

/// 표현 변환기: 투영된 값들을 다른 표현으로 변환
pub trait Representation<T: Eq + std::hash::Hash + Clone>: Debug {
    fn represent(&self, values: &HashSet<T>) -> HashSet<String>;
}

#[derive(Debug)]
pub struct NextValues;
#[derive(Debug)]
pub struct OperationType;
#[derive(Debug)]
pub struct Magnitude;

impl Representation<i64> for NextValues {
    fn represent(&self, values: &HashSet<i64>) -> HashSet<String> {
        values.iter().map(|&x| format!("Next: {}", x + 1)).collect()
    }
}

impl Representation<i64> for OperationType {
    fn represent(&self, values: &HashSet<i64>) -> HashSet<String> {
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

impl Representation<i64> for Magnitude {
    fn represent(&self, values: &HashSet<i64>) -> HashSet<String> {
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

/// 상태 공간 계층 구조
pub trait StateSpaceHierarchy {
    /// 포함 관계: 다른 상태 공간을 포함하는가?
    fn contains<S: StateSpace>(&self, other: &S) -> bool;

    /// 교차 관계: 다른 상태 공간과 교차하는가?
    fn intersects<S: StateSpace>(&self, other: &S) -> bool;
}

/// 투영자 예시들
pub mod projectors {
    use super::*;

    /// 정수 투영자: 좌표의 첫 번째 원소를 정수로 해석
    #[derive(Debug)]
    pub struct IntegerProjector {
        axis_index: usize, // 좌표 벡터 내 인덱스
    }

    impl IntegerProjector {
        pub fn new(axis_index: usize) -> Self {
            Self { axis_index }
        }

        pub fn default() -> Self {
            Self { axis_index: 0 }
        }
    }

    impl SpaceProjector for IntegerProjector {
        type Output = i64;

        fn project<S: StateSpace>(&self, space: &S) -> Option<i64> {
            let coords = space.coordinates();
            if coords.raw.len() > self.axis_index {
                Some(coords.raw[self.axis_index])
            } else {
                None
            }
        }

        fn target_dimension(&self) -> ProjectionAxis {
            ProjectionAxis::Integer
        }

        fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
            coordinates.raw.len() > self.axis_index
        }
    }

    /// 불리언 투영자: 좌표의 첫 번째 원소를 0/1으로 해석
    #[derive(Debug)]
    pub struct BooleanProjector {
        axis_index: usize,
        true_value: i64,
        false_value: i64,
    }

    impl BooleanProjector {
        pub fn new(axis_index: usize, true_value: i64, false_value: i64) -> Self {
            Self {
                axis_index,
                true_value,
                false_value,
            }
        }

        pub fn default() -> Self {
            Self {
                axis_index: 0,
                true_value: 1,
                false_value: 0,
            }
        }
    }

    impl SpaceProjector for BooleanProjector {
        type Output = bool;

        fn project<S: StateSpace>(&self, space: &S) -> Option<bool> {
            let coords = space.coordinates();
            if coords.raw.len() > self.axis_index {
                let value = coords.raw[self.axis_index];
                Some(value == self.true_value)
            } else {
                None
            }
        }

        fn target_dimension(&self) -> ProjectionAxis {
            ProjectionAxis::Boolean
        }

        fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
            coordinates.raw.len() > self.axis_index
        }
    }
}

/// 제약조건 투영자: constraint()를 불리언으로 투영
#[derive(Debug)]
pub struct ConstraintProjector;

impl SpaceProjector for ConstraintProjector {
    type Output = bool;

    fn project<S: StateSpace>(&self, space: &S) -> Option<bool> {
        Some(space.constraint())
    }

    fn target_dimension(&self) -> ProjectionAxis {
        ProjectionAxis::Boolean
    }

    fn can_project(&self, _coordinates: &SpaceCoordinates) -> bool {
        true // constraint()는 항상 존재
    }
}

// arithmetic.qs 파일 직접 포함
pub mod arithmetic {
    include!("../spaces/arithmetic.qs");
}

// boolean.qs 파일 직접 포함
pub mod boolean {
    include!("../spaces/boolean.qs");
}

// 공용 타입들을 루트에 재내보내기
pub use arithmetic::{ArithmeticConstraint, ArithmeticSpace};
pub use boolean::{BooleanConstraint, BooleanSpace};
