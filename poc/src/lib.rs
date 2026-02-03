//! Quasar: State-Space Driven Non-Deterministic Computing
//!
//! 핵심 철학:
//! 1. StateSpace는 불변 구조적 식별자
//! 2. 좌표(SpaceCoordinates)는 의미 없는 구조적 위치
//! 3. 의미는 투영자(Projector)에 의해 창발
//! 4. 제약조건은 허용 영역 정의
//! 5. 관측자는 기대값과 비교
//!
//! Future Work:
//! - Field 시스템: 동적 연산 계층
//! - 제약조건 네트워크: 상호작용하는 제약조건들
//! - 전이 네트워크: 상태 간 동적 연결

//! Quasar: State-Space Driven Non-Deterministic Computing
//!
//! 핵심 철학:
//! 1. StateSpace = 좌표 + 제약조건 (구조적 제한)
//! 2. Projector = 좌표 → 값 변환 (의미적 해석)
//! 3. Observer = 투영 결과 검증 (기대값 비교)

//! Quasar: State-Space Driven Non-Deterministic Computing
//!
//! 핵심 철학:
//! 1. StateSpace = 불변 구조 (좌표 + 제약조건)
//! 2. Constraint = 구조적 제한 (허용 영역)
//! 3. Projector = 구조 → 의미 변환
//! 4. Observer = 의미 검증

//! Quasar: State-Space Driven Non-Deterministic Computing
//!
//! 핵심 계층:
//! 1. StateSpace: 불변 구조 (좌표 + 기본 인접성)
//! 2. StateField: StateSpace + 동적 Field 요소 (전이, 제약, 관측)
//! 3. Projector/Observer: 의미 창발 시스템

use std::collections::HashSet;
use std::fmt::Debug;
use std::hash::Hash;
use std::marker::PhantomData;
use std::sync::Arc;
// ==================== CORE TYPES ====================

/// 불변 구조적 좌표
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct SpaceCoordinates {
    pub raw: Vec<i64>,
}

impl SpaceCoordinates {
    pub fn new(raw: Vec<i64>) -> Self {
        Self { raw }
    }
    pub fn dimensionality(&self) -> usize {
        self.raw.len()
    }
    pub fn get_axis(&self, axis: usize) -> Option<i64> {
        self.raw.get(axis).copied()
    }
}

// ==================== CONSTRAINT SYSTEM ====================

pub trait Constraint: Debug + Send + Sync {
    fn allows(&self, coords: &SpaceCoordinates) -> bool;
    fn describe(&self) -> String;
}

#[derive(Debug, Clone)]
pub struct ConstraintSet {
    constraints: Vec<Arc<dyn Constraint>>,
}

impl ConstraintSet {
    pub fn new() -> Self {
        Self {
            constraints: Vec::new(),
        }
    }
    pub fn add<C: Constraint + 'static>(&mut self, constraint: C) {
        self.constraints.push(Arc::new(constraint));
    }
    pub fn allows(&self, coords: &SpaceCoordinates) -> bool {
        self.constraints.iter().all(|c| c.allows(coords))
    }
    pub fn describe(&self) -> String {
        if self.constraints.is_empty() {
            "No constraints".into()
        } else {
            self.constraints
                .iter()
                .map(|c| c.describe())
                .collect::<Vec<_>>()
                .join(", ")
        }
    }
}

// ==================== STATE SPACE TRAIT ====================

/// 불변 상태 공간: 좌표 + 기본 인접성
pub trait StateSpace: Debug + Clone {
    fn coordinates(&self) -> SpaceCoordinates;
    fn basic_adjacency(&self) -> Vec<SpaceCoordinates>; // 구조적 인접성만 정의
}

// ==================== STATE FIELD ====================

/// StateField: StateSpace + 동적 Field 요소들
/// - StateSpace는 불변, Field 요소들은 가변/재구성 가능
#[derive(Debug, Clone)]
pub struct StateField<S, O, V>
where
    S: StateSpace,
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
{
    pub space: S,                                    // 불변 StateSpace
    pub transition_matrix: TransitionMatrix,         // 전이 규칙
    pub constraints: ConstraintSet,                  // 동적 제약조건
    pub observation_config: ObservationConfig<O, V>, // 관측 설정
}

impl<S: StateSpace, O, V> StateField<S, O, V>
where
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
{
    pub fn new(space: S) -> Self {
        Self {
            space,
            transition_matrix: TransitionMatrix::default(),
            constraints: ConstraintSet::new(),
            observation_config: ObservationConfig::<O, V>::default(),
        }
    }

    /// 제약조건 추가 (새 StateField 반환)
    pub fn with_constraint(mut self, constraint: impl Constraint + 'static) -> Self {
        self.constraints.add(constraint);
        self
    }

    /// 전이 규칙 설정
    pub fn with_transition(
        mut self,
        from: SpaceCoordinates,
        to: SpaceCoordinates,
        weight: f64,
    ) -> Self {
        self.transition_matrix.add(from, to, weight);
        self
    }

    /// 현재 좌표가 모든 제약조건을 만족하는지
    pub fn is_allowed(&self) -> bool {
        self.constraints.allows(&self.space.coordinates())
    }

    /// 가능한 다음 상태들 (제약조건 고려)
    pub fn possible_transitions(&self) -> Vec<S>
    where
        S: From<SpaceCoordinates>,
    {
        let current = self.space.coordinates();

        // 1. 기본 구조적 인접성
        let basic = self.space.basic_adjacency();

        // 2. 전이 행렬 기반 인접성
        let from_transitions = self.transition_matrix.transitions_from(&current);

        // 3. 병합하고 제약조건 필터링
        basic
            .into_iter()
            .chain(from_transitions)
            .filter(|coord| self.constraints.allows(coord))
            .map(S::from)
            .collect()
    }

    /// 상태 트리 생성 (제약조건 만족하는 전이만)
    pub fn generate_tree(&self, max_depth: usize) -> HashSet<S>
    where
        S: From<SpaceCoordinates> + std::hash::Hash + Eq,
    {
        let mut visited = HashSet::new();
        let mut result = HashSet::new();
        let mut stack = vec![(self.space.clone(), 0)];

        while let Some((state, depth)) = stack.pop() {
            if !visited.insert(state.coordinates()) {
                continue;
            }
            result.insert(state.clone());

            if depth >= max_depth {
                continue;
            }

            // 현재 StateField에서의 전이 계산
            let field = StateField {
                space: state,
                transition_matrix: self.transition_matrix.clone(),
                constraints: self.constraints.clone(),
                observation_config: self.observation_config.clone(),
            };

            for next_state in field.possible_transitions() {
                if !visited.contains(&next_state.coordinates()) {
                    stack.push((next_state, depth + 1));
                }
            }
        }

        result
    }
}

// ==================== TRANSITION MATRIX ====================

/// 전이 행렬: 상태 간 전이 규칙 정의
#[derive(Debug, Clone, Default)]
pub struct TransitionMatrix {
    pub transitions: Vec<(SpaceCoordinates, SpaceCoordinates, f64)>,
}

impl TransitionMatrix {
    pub fn add(&mut self, from: SpaceCoordinates, to: SpaceCoordinates, weight: f64) {
        self.transitions.push((from, to, weight));
    }

    pub fn transitions_from(&self, from: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        self.transitions
            .iter()
            .filter(|(f, _, _)| f == from)
            .map(|(_, t, _)| t.clone())
            .collect()
    }

    pub fn get_weight(&self, from: &SpaceCoordinates, to: &SpaceCoordinates) -> Option<f64> {
        self.transitions
            .iter()
            .find(|(f, t, _)| f == from && t == to)
            .map(|(_, _, w)| *w)
    }
}

// ==================== OBSERVATION CONFIG ====================

/// 관측 설정: 투영자와 관측자 설정
#[derive(Debug, Clone)]
pub struct ObservationConfig<O, V>
where
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
{
    projectors: Vec<Arc<dyn Projector<Output = O>>>,
    observers: Vec<Arc<dyn Observer<Value = V>>>,
}

impl<O, V> ObservationConfig<O, V>
where
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
{
    pub fn add_projector<P>(&mut self, projector: P)
    where
        P: Projector<Output = O> + 'static,
    {
        self.projectors.push(Arc::new(projector));
    }

    pub fn add_observer<Obs>(&mut self, observer: Obs)
    where
        Obs: Observer<Value = V> + 'static,
    {
        self.observers.push(Arc::new(observer));
    }

    fn default() -> Self {
        Self {
            projectors: Vec::new(),
            observers: Vec::new(),
        }
    }
}

// ==================== PROJECTOR & OBSERVER ====================

pub trait Projector: Debug + Send + Sync {
    type Output: Eq + Hash + Clone + Debug;
    fn project(&self, coords: &SpaceCoordinates) -> Option<Self::Output>;
    fn can_project(&self, coords: &SpaceCoordinates) -> bool;
}

pub trait Observer: Debug + Send + Sync {
    type Value: Eq + Hash + Clone + Debug;
    fn observe(&self, value: &Self::Value) -> bool;
    fn describe(&self) -> String;
}

/// 정수 투영자
#[derive(Debug, Clone)]
pub struct IntegerProjector {
    axis: usize,
}

impl IntegerProjector {
    pub fn new(axis: usize) -> Self {
        Self { axis }
    }
}

impl Projector for IntegerProjector {
    type Output = i64;
    fn project(&self, coords: &SpaceCoordinates) -> Option<i64> {
        coords.get_axis(self.axis)
    }
    fn can_project(&self, coords: &SpaceCoordinates) -> bool {
        coords.get_axis(self.axis).is_some()
    }
}

/// 값 비교 관측자
#[derive(Debug, Clone)]
pub struct ValueObserver<T: Eq + Debug> {
    expected: T,
    description: String,
}

impl<T: Eq + Debug + Clone + 'static> ValueObserver<T> {
    pub fn new(expected: T, description: &str) -> Self {
        Self {
            expected,
            description: description.to_string(),
        }
    }
}

impl<T> Observer for ValueObserver<T>
where
    T: Eq + Hash + Clone + Debug + Send + Sync + 'static,
{
    type Value = T;

    fn observe(&self, value: &Self::Value) -> bool {
        value == &self.expected
    }

    fn describe(&self) -> String {
        self.description.clone()
    }
}

// ==================== CORE FUNCTIONS ====================

/// StateField에서 관측 수행
pub fn observe_field<S, O, V, P>(field: &StateField<S, O, V>, projector: &P) -> Option<P::Output>
where
    S: StateSpace,
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
    P: Projector<Output = O>,
{
    if field.is_allowed() {
        projector.project(&field.space.coordinates())
    } else {
        None
    }
}

pub fn observe_tree<S, O, V, P>(
    field: &StateField<S, O, V>,
    projector: &P,
    max_depth: usize,
) -> HashSet<P::Output>
where
    S: StateSpace + From<SpaceCoordinates> + std::hash::Hash + Eq,
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
    P: Projector<Output = O>,
    P::Output: Eq + std::hash::Hash + Clone,
{
    let mut results = HashSet::new();

    for state in field.generate_tree(max_depth) {
        let temp_field = StateField {
            space: state,
            transition_matrix: field.transition_matrix.clone(),
            constraints: field.constraints.clone(),
            observation_config: field.observation_config.clone(),
        };

        if let Some(value) = observe_field(&temp_field, projector) {
            results.insert(value);
        }
    }

    results
}

/// 상태 공간 합성 (old.txt의 compose_spaces와 유사)
pub fn compose_fields<S1, S2, O1, V1, O2, V2>(
    field1: &StateField<S1, O1, V1>,
    field2: &StateField<S2, O2, V2>,
) -> CompositionResult
where
    S1: StateSpace,
    S2: StateSpace,
    O1: Eq + Hash + Clone + Debug + 'static,
    V1: Eq + Hash + Clone + Debug + 'static,
    ObservationConfig<O1, V1>: Default,
    O2: Eq + Hash + Clone + Debug + 'static,
    V2: Eq + Hash + Clone + Debug + 'static,
    ObservationConfig<O2, V2>: Default,
{
    let both_allowed = field1.is_allowed() && field2.is_allowed();
    CompositionResult {
        space1_allowed: field1.is_allowed(),
        space2_allowed: field2.is_allowed(),
        both_allowed,
        compatibility: if both_allowed {
            "Compatible"
        } else {
            "Incompatible"
        }
        .into(),
    }
}

impl<O, V> Default for ObservationConfig<O, V>
where
    O: Eq + Hash + Clone + Debug + 'static,
    V: Eq + Hash + Clone + Debug + 'static,
{
    fn default() -> Self {
        Self {
            projectors: Vec::new(),
            observers: Vec::new(),
        }
    }
}

#[derive(Debug)]
pub struct CompositionResult {
    pub space1_allowed: bool,
    pub space2_allowed: bool,
    pub both_allowed: bool,
    pub compatibility: String,
}

// ==================== CONSTRAINT IMPLEMENTATIONS ====================

/// 범위 제약조건 (old.txt InRange 참고)
#[derive(Debug, Clone)]
pub struct RangeConstraint {
    axis: usize,
    min: i64,
    max: i64,
}

impl RangeConstraint {
    pub fn new(axis: usize, min: i64, max: i64) -> Self {
        Self { axis, min, max }
    }
}

impl Constraint for RangeConstraint {
    fn allows(&self, coords: &SpaceCoordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v >= self.min && v <= self.max)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] ∈ [{}, {}]", self.axis, self.min, self.max)
    }
}

/// 짝수 제약조건 (old.txt Even 참고)
#[derive(Debug, Clone)]
pub struct EvenConstraint {
    axis: usize,
}

impl EvenConstraint {
    pub fn new(axis: usize) -> Self {
        Self { axis }
    }
}

impl Constraint for EvenConstraint {
    fn allows(&self, coords: &SpaceCoordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v % 2 == 0)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] is even", self.axis)
    }
}

// ==================== MODULE STRUCTURE ====================

pub mod fields {
    use super::*;

    /// StateField 빌더 패턴
    pub struct FieldBuilder<S, O, V>
    where
        S: StateSpace,
        O: Eq + Hash + Clone + Debug + 'static,
        V: Eq + Hash + Clone + Debug + 'static,
    {
        space: S,
        constraints: Vec<Arc<dyn Constraint>>,
        transitions: Vec<(SpaceCoordinates, SpaceCoordinates, f64)>,
        _marker: PhantomData<(O, V)>,
    }

    impl<S, O, V> FieldBuilder<S, O, V>
    where
        S: StateSpace,
        O: Eq + Hash + Clone + Debug + 'static,
        V: Eq + Hash + Clone + Debug + 'static,
        ObservationConfig<O, V>: Default,
    {
        pub fn new(space: S) -> Self {
            Self {
                space,
                constraints: Vec::new(),
                transitions: Vec::new(),
                _marker: PhantomData,
            }
        }

        pub fn add_constraint<C: Constraint + 'static>(mut self, constraint: C) -> Self {
            self.constraints.push(Arc::new(constraint));
            self
        }

        pub fn add_transition(mut self, to: SpaceCoordinates, weight: f64) -> Self {
            let from = self.space.coordinates();
            self.transitions.push((from.clone(), to, weight));
            self
        }

        pub fn build(self) -> StateField<S, O, V> {
            let mut field: StateField<S, O, V> = StateField::<S, O, V>::new(self.space);

            for constraint in self.constraints {
                field.constraints.constraints.push(constraint);
            }

            for (from, to, weight) in self.transitions {
                field.transition_matrix.add(from, to, weight);
            }

            field
        }
    }
}

// ==================== MODULE STRUCTURE ====================

pub mod spaces {
    // arithmetic.ss
    #[path = "../spaces/arithmetic.ss"]
    pub mod arithmetic;

    // basic.ss
    #[path = "../spaces/basic.ss"]
    pub mod basic;
}
pub use spaces::*;
