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

    /// 좌표 벡터 참조
    pub fn as_slice(&self) -> &[i64] {
        &self.raw
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

/// 좌표 투영자: SpaceCoordinates를 특정 값으로 투영하는 순수한 해석 도구
/// StateSpace 타입에 의존하지 않음
pub trait CoordinateProjector: Debug {
    type Output: Eq + std::hash::Hash + Clone + Debug;

    /// 좌표를 특정 값으로 투영
    fn project_coordinates(&self, coordinates: &SpaceCoordinates) -> Option<Self::Output>;

    /// 투영 가능 여부
    fn can_project(&self, coordinates: &SpaceCoordinates) -> bool;
}

/// 관측자: 특정 투영 결과를 기대하는 투영자 래퍼
#[derive(Debug)]
pub struct Observer<P: CoordinateProjector> {
    projector: P,
    expected: P::Output,
}

impl<P: CoordinateProjector> Observer<P> {
    pub fn new(projector: P, expected: P::Output) -> Self {
        Self {
            projector,
            expected,
        }
    }

    /// 관측: 좌표가 기대값으로 투영되는지 확인
    pub fn observe(&self, coordinates: &SpaceCoordinates) -> Option<bool> {
        self.projector
            .project_coordinates(coordinates)
            .map(|value| value == self.expected)
    }
}

/// 상태 공간 투영 도우미 함수
pub fn project_space<P: CoordinateProjector, S: StateSpace>(
    projector: &P,
    space: &S,
) -> Option<P::Output> {
    if space.constraint() {
        projector.project_coordinates(&space.coordinates())
    } else {
        None
    }
}

/// 상태 집합 관측 함수
pub fn observe_space<P: CoordinateProjector, S: StateSpace>(
    states: &HashSet<S>,
    projector: &P,
) -> HashSet<P::Output>
where
    P::Output: Eq + std::hash::Hash + Clone,
{
    let mut results = HashSet::new();

    for state in states {
        if let Some(value) = project_space(projector, state) {
            results.insert(value);
        }
    }

    results
}

/// 조건부 전이 관측 함수
pub fn observe_transitions<P: CoordinateProjector, S: StateSpace>(
    states: &HashSet<S>,
    observer: &Observer<P>,
) -> HashSet<P::Output>
where
    P: CoordinateProjector,
    P::Output: Eq + std::hash::Hash + Clone + Debug,
{
    let mut results = HashSet::new();

    for state in states {
        if !state.constraint() {
            continue;
        }

        // 좌표 관측
        if let Some(true) = observer.observe(&state.coordinates()) {
            // 전이 상태들의 좌표 투영
            for next in state.transitions() {
                if next.constraint() {
                    if let Some(value) = observer.projector.project_coordinates(&next.coordinates())
                    {
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

/// 좌표 투영자 예시들
pub mod projectors {
    use super::*;

    /// 정수 투영자: 좌표의 특정 인덱스를 정수로 해석
    #[derive(Debug)]
    pub struct IntegerProjector {
        axis_index: usize,
    }

    impl IntegerProjector {
        pub fn new(axis_index: usize) -> Self {
            Self { axis_index }
        }

        pub fn default() -> Self {
            Self { axis_index: 0 }
        }
    }

    impl CoordinateProjector for IntegerProjector {
        type Output = i64;

        fn project_coordinates(&self, coordinates: &SpaceCoordinates) -> Option<i64> {
            coordinates.as_slice().get(self.axis_index).copied()
        }

        fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
            coordinates.as_slice().len() > self.axis_index
        }
    }

    /// 불리언 투영자: 좌표의 특정 인덱스를 불리언으로 해석
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

        pub fn standard() -> Self {
            Self {
                axis_index: 0,
                true_value: 1,
                false_value: 0,
            }
        }

        fn interpret(&self, value: i64) -> Option<bool> {
            if value == self.true_value {
                Some(true)
            } else if value == self.false_value {
                Some(false)
            } else {
                None
            }
        }
    }

    impl CoordinateProjector for BooleanProjector {
        type Output = bool;

        fn project_coordinates(&self, coordinates: &SpaceCoordinates) -> Option<bool> {
            coordinates
                .as_slice()
                .get(self.axis_index)
                .and_then(|&value| self.interpret(value))
        }

        fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
            coordinates
                .as_slice()
                .get(self.axis_index)
                .map_or(false, |&value| {
                    value == self.true_value || value == self.false_value
                })
        }
    }

    /// 범위 투영자: 좌표가 특정 범위에 있는지 확인
    #[derive(Debug)]
    pub struct RangeProjector {
        axis_index: usize,
        min: i64,
        max: i64,
    }

    impl RangeProjector {
        pub fn new(axis_index: usize, min: i64, max: i64) -> Self {
            Self {
                axis_index,
                min,
                max,
            }
        }
    }

    impl CoordinateProjector for RangeProjector {
        type Output = bool;

        fn project_coordinates(&self, coordinates: &SpaceCoordinates) -> Option<bool> {
            coordinates
                .as_slice()
                .get(self.axis_index)
                .map(|&value| value >= self.min && value <= self.max)
        }

        fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
            coordinates.as_slice().len() > self.axis_index
        }
    }

    /// 다차원 투영자: 여러 축을 조합한 투영
    #[derive(Debug)]
    pub struct MultiAxisProjector {
        axis_indices: Vec<usize>,
        separator: String,
    }

    impl MultiAxisProjector {
        pub fn new(axis_indices: Vec<usize>, separator: &str) -> Self {
            Self {
                axis_indices,
                separator: separator.to_string(),
            }
        }
    }

    impl CoordinateProjector for MultiAxisProjector {
        type Output = String;

        fn project_coordinates(&self, coordinates: &SpaceCoordinates) -> Option<String> {
            let values: Vec<String> = self
                .axis_indices
                .iter()
                .filter_map(|&idx| coordinates.as_slice().get(idx))
                .map(|v| v.to_string())
                .collect();

            if values.is_empty() {
                None
            } else {
                Some(values.join(&self.separator))
            }
        }

        fn can_project(&self, coordinates: &SpaceCoordinates) -> bool {
            self.axis_indices
                .iter()
                .all(|&idx| coordinates.as_slice().len() > idx)
        }
    }
}

/// 제약조건 투영자: constraint()를 투영하는 특수한 경우
/// 이 투영자는 StateSpace에 의존하지만, 개념적으로는 상태의 "제약 만족 여부"를 투영
#[derive(Debug)]
pub struct ConstraintSatisfactionProjector;

impl CoordinateProjector for ConstraintSatisfactionProjector {
    type Output = bool;

    fn project_coordinates(&self, _coordinates: &SpaceCoordinates) -> Option<bool> {
        // 이 투영자는 좌표만으로는 constraint를 알 수 없음
        // StateSpace의 constraint() 메서드가 필요
        // 따라서 이 투영자는 특별한 경우임
        None
    }

    fn can_project(&self, _coordinates: &SpaceCoordinates) -> bool {
        false // 좌표만으로는 constraint를 알 수 없음
    }
}

// arithmetic.qs 파일 직접 포함
pub mod arithmetic {
    include!("../spaces/arithmetic.qs");
}
pub use arithmetic::{ArithmeticConstraint, ArithmeticSpace};

// boolean.qs 파일 직접 포함
pub mod boolean {
    include!("../spaces/boolean.qs");
}
pub use boolean::{BooleanConstraint, BooleanSpace};
