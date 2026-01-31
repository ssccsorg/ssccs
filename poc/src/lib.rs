//! SSCCS State-Space Computing Core
//! 철학: StateSpace는 값을 "가지지" 않음, 값은 투영의 결과물

mod constrainable;
pub use constrainable::*;

use std::collections::HashSet;
use std::fmt::Debug;

/// 투명한 구조적 좌표 - 의미 해석 금지
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct SpaceCoordinates {
    /// 투명한 구조적 좌표
    pub raw: Vec<i64>,
}

impl SpaceCoordinates {
    /// 새로운 투명 좌표 생성
    pub fn new(raw: Vec<i64>) -> Self {
        Self { raw }
    }

    /// 좌표 벡터 참조
    pub fn as_slice(&self) -> &[i64] {
        &self.raw
    }
}

/// 제약조건 집합 - 허용된 좌표들의 집합
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ConstraintSet {
    /// 허용 좌표들
    pub allowed: HashSet<SpaceCoordinates>,
}

impl ConstraintSet {
    /// 새로운 제약조건 집합 생성
    pub fn new(allowed: HashSet<SpaceCoordinates>) -> Self {
        Self { allowed }
    }

    /// 특정 좌표가 허용되는지 확인
    pub fn allows(&self, coord: &SpaceCoordinates) -> bool {
        self.allowed.contains(coord)
    }

    pub fn empty() -> Self {
        Self {
            allowed: HashSet::new(),
        }
    }

    /// 두 제약조건 집합의 합성 (교집합)
    pub fn compose(&self, other: &ConstraintSet) -> Self {
        let allowed: HashSet<_> = self.allowed.intersection(&other.allowed).cloned().collect();

        Self { allowed }
    }

    /// 편의 메서드: 현재 좌표만 허용하는 집합 생성
    pub fn singleton(coord: SpaceCoordinates) -> Self {
        let mut allowed = HashSet::new();
        allowed.insert(coord);
        Self::new(allowed)
    }
}

/// 상태 공간: 가능성의 공간
/// 상태 공간: 가능성의 공간
pub trait StateSpace: Clone + PartialEq + Eq + std::hash::Hash {
    /// 이 상태 공간의 "좌표"
    fn coordinates(&self) -> SpaceCoordinates;

    /// 제약조건 집합 반환 (순환 참조를 피하기 위해 좌표만으로 계산)
    fn constraint_set(&self) -> ConstraintSet;

    /// 현재 좌표가 허용되는지 확인 (편의 메서드)
    fn allows(&self) -> bool {
        self.constraint_set().allows(&self.coordinates())
    }

    /// 특정 좌표가 허용되는지 확인
    fn allows_coordinate(&self, coord: &SpaceCoordinates) -> bool {
        self.constraint_set().allows(coord)
    }

    /// 전이 가능한 상태 공간들 (제약조건 만족 여부 검사 없이 생성)
    fn possible_transitions(&self) -> HashSet<Self>; // Vec → HashSet

    /// 제약조건을 만족하는 전이들만 반환
    fn valid_transitions(&self) -> HashSet<Self> {
        // Vec → HashSet
        self.possible_transitions()
            .into_iter()
            .filter(|state| state.allows())
            .collect()
    }

    /// 상태 트리 생성 (순환 참조 방지)
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

            // valid_transitions만 사용 (순환 참조 없음)
            for next in state.valid_transitions() {
                if !visited.contains(&next) {
                    stack.push(next);
                }
            }
        }

        result
    }
}

/// 좌표 투영자: SpaceCoordinates를 특정 값으로 투영하는 순수한 해석 도구
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
    if space.allows() {
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
        if !state.allows() {
            continue;
        }

        // 좌표 관측
        if let Some(true) = observer.observe(&state.coordinates()) {
            // 전이 상태들의 좌표 투영
            for next in state.valid_transitions() {
                if next.allows() {
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
}

/// 두 상태 공간의 합성
pub fn compose_spaces<S1: StateSpace, S2: StateSpace>(space1: &S1, space2: &S2) -> CompositeSpace {
    CompositeSpace::new(
        space1.constraint_set(),
        space2.constraint_set(),
        format!("{:?}", space1.coordinates()),
        format!("{:?}", space2.coordinates()),
    )
}

/// 합성된 상태 공간
#[derive(Clone, Debug)]
pub struct CompositeSpace {
    constraint_set: ConstraintSet,
    space1_description: String,
    space2_description: String,
    /// 합성 결과 통계
    statistics: CompositionStatistics,
}

#[derive(Clone, Debug)]
pub struct CompositionStatistics {
    pub total_space1_allowed: usize,
    pub total_space2_allowed: usize,
    pub intersection_size: usize,
    pub composition_ratio: f64, // 교집합 크기 / (space1 ∪ space2) 크기
}

impl CompositeSpace {
    pub fn new(
        set1: ConstraintSet,
        set2: ConstraintSet,
        space1_desc: String,
        space2_desc: String,
    ) -> Self {
        let total_space1_allowed = set1.allowed.len();
        let total_space2_allowed = set2.allowed.len();
        let intersection: HashSet<_> = set1.allowed.intersection(&set2.allowed).cloned().collect();
        let intersection_size = intersection.len();

        let union_size = set1.allowed.union(&set2.allowed).count();
        let composition_ratio = if union_size > 0 {
            intersection_size as f64 / union_size as f64
        } else {
            0.0
        };

        let statistics = CompositionStatistics {
            total_space1_allowed,
            total_space2_allowed,
            intersection_size,
            composition_ratio,
        };

        Self {
            constraint_set: set1.compose(&set2),
            space1_description: space1_desc,
            space2_description: space2_desc,
            statistics,
        }
    }

    pub fn constraint_set(&self) -> &ConstraintSet {
        &self.constraint_set
    }

    /// 허용 좌표들
    pub fn allowed_coordinates(&self) -> &HashSet<SpaceCoordinates> {
        &self.constraint_set.allowed
    }

    /// 합성 통계
    pub fn statistics(&self) -> &CompositionStatistics {
        &self.statistics
    }

    /// 합성 정보 출력
    pub fn describe_composition(&self) -> String {
        format!(
            "합성: {} ∩ {}\n\
            Space1 허용: {}개 좌표\n\
            Space2 허용: {}개 좌표\n\
            교집합: {}개 좌표\n\
            합성 비율: {:.1}%",
            self.space1_description,
            self.space2_description,
            self.statistics.total_space1_allowed,
            self.statistics.total_space2_allowed,
            self.statistics.intersection_size,
            self.statistics.composition_ratio * 100.0
        )
    }

    /// 특정 좌표가 두 공간 모두에서 허용되는지 확인
    pub fn is_fully_allowed(&self, coord: &SpaceCoordinates) -> bool {
        self.constraint_set.allows(coord)
    }

    /// 경계면 좌표 찾기 (한쪽은 허용하지만 다른쪽은 허용하지 않는 좌표)
    pub fn find_boundary_coordinates(
        &self,
        set1: &ConstraintSet,
        set2: &ConstraintSet,
    ) -> HashSet<SpaceCoordinates> {
        let mut boundaries = HashSet::new();

        // set1만 허용하는 좌표들
        for coord in &set1.allowed {
            if !set2.allows(coord) {
                boundaries.insert(coord.clone());
            }
        }

        // set2만 허용하는 좌표들
        for coord in &set2.allowed {
            if !set1.allows(coord) {
                boundaries.insert(coord.clone());
            }
        }

        boundaries
    }
}

// arithmetic.ss 파일 직접 포함
pub mod arithmetic {
    include!("../spaces/arithmetic.ss");
}
pub use arithmetic::{ArithmeticConstraint, ArithmeticSpace};

// boolean.ss 파일 직접 포함
pub mod boolean {
    include!("../spaces/boolean.ss");
}
pub use boolean::{BooleanConstraint, BooleanSpace};
