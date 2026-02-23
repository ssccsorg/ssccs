// qs-core/poc/src/scheme.rs
//! Scheme 추상화 계층 - 물리적 메모리 구현 없이 구조적 관계 정의
//! 새로운 Scheme 추상화: 구조적 관계, 축 시스템, 메모리 레이아웃 추상화, 관찰 규칙

use crate::core::{Constraint, Segment, SegmentId, SpaceCoordinates};

use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::hash::Hash;
use std::sync::Arc;

// ==================== SCHEME IDENTITY ====================

/// Scheme의 암호화 식별자
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct SchemeId([u8; 32]);

impl SchemeId {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }

    pub fn to_hex(&self) -> String {
        hex::encode(self.0)
    }
}

// ==================== DIMENSIONAL ABSTRACTION ====================

/// 차원 축의 추상적 정의
#[derive(Clone, Debug, PartialEq)]
pub struct Axis {
    /// 축 이름 (예: "x", "y", "time", "energy")
    pub name: String,

    /// 축 유형 - 구현체가 물리적 표현을 결정
    pub axis_type: AxisType,

    /// 축 메타데이터 (선택적)
    pub metadata: HashMap<String, String>,
}

/// 축 유형 - 물리적 표현 없이 의미만 정의
#[derive(Clone, Debug, PartialEq)]
pub enum AxisType {
    /// 이산 축 (정수값)
    Discrete,

    /// 연속 축 (실수값, 물리적 해상도는 구현체가 결정)
    Continuous,

    /// 순환 축 (주기적, 예: 각도 0-360)
    Cyclic(Option<i64>), // 주기 (선택적)

    /// 범주형 축 (이산적 카테고리)
    Categorical,

    /// 관계형 축 (다른 축과의 관계 정의)
    Relational(String), // 관련 축 이름

    /// 측정 단위가 있는 축
    WithUnit(String), // 단위 (예: "meters", "seconds")
}

// ==================== STRUCTURAL RELATIONS ====================

/// Segment 간 구조적 관계
#[derive(Clone, Debug, PartialEq)]
pub enum StructuralRelation {
    /// 인접 관계 (공간적/개념적 근접성)
    Adjacency {
        relation_type: AdjacencyType,
        weight: Option<f64>, // 관계 강도 (선택적)
        metadata: HashMap<String, String>,
    },

    /// 계층 관계 (부모-자식)
    Hierarchy {
        parent: SegmentId,
        depth: i64,
        relation_type: HierarchyType,
    },

    /// 의존 관계 (A가 B에 의존)
    Dependency {
        dependent: SegmentId,
        dependency_type: DependencyType,
        strength: f64,
    },

    /// 동등 관계 (동일 구조 내 다른 표현)
    Equivalence {
        equivalence_class: u64,
        symmetry: SymmetryType,
    },

    /// 사용자 정의 관계
    Custom {
        name: String,
        predicate: Arc<dyn Fn(&Segment, &Segment) -> bool + Send + Sync>,
    },
}

/// 인접성 유형
#[derive(Clone, Debug, PartialEq)]
pub enum AdjacencyType {
    /// 유클리드 거리 기준
    Euclidean(f64), // 거리 임계값

    /// 맨해튼 거리 기준
    Manhattan(i64), // L1 거리 임계값

    /// 격자 이웃 (2D/3D 그리드)
    Grid(GridTopology),

    /// 그래프 연결 (임의 토폴로지)
    Graph,

    /// 시공간 인접 (시간 + 공간)
    Spatiotemporal,

    /// 개념적 인접 (의미적 유사성)
    Conceptual,
}

/// 그리드 토폴로지
#[derive(Clone, Debug, PartialEq)]
pub enum GridTopology {
    FourConnected,           // 상하좌우
    EightConnected,          // 대각선 포함
    Hexagonal,               // 육각 그리드
    Triangular,              // 삼각 그리드
    Custom(Vec<(i64, i64)>), // 사용자 정의 오프셋
}

/// 계층 관계 유형
#[derive(Clone, Debug, PartialEq)]
pub enum HierarchyType {
    Containment,    // 포함 관계
    Inheritance,    // 상속 관계
    Composition,    // 구성 관계
    Specialization, // 특수화 관계
}

/// 의존성 유형
#[derive(Clone, Debug, PartialEq)]
pub enum DependencyType {
    DataFlow,    // 데이터 흐름
    ControlFlow, // 제어 흐름
    Temporal,    // 시간적 의존
    Causal,      // 인과 관계
    Resource,    // 자원 의존
}

/// 대칭성 유형
#[derive(Clone, Debug, PartialEq)]
pub enum SymmetryType {
    Symmetric,  // 양방향 동등
    Asymmetric, // 단방향 동등
    Reflexive,  // 자기 동등
    Transitive, // 추이적
}

// ==================== STRUCTURAL CONSTRAINTS ====================

/// 구조적 제약 (Scheme 수준의 불변 제약)
#[derive(Clone, Debug)]
pub struct StructuralConstraint {
    /// 제약 조건 (Field 제약과 구분)
    constraint: Arc<dyn Constraint>,

    /// 제약 유형
    constraint_type: ConstraintType,

    /// 적용 범위
    scope: ConstraintScope,
}

/// 제약 유형
#[derive(Clone, Debug, PartialEq)]
pub enum ConstraintType {
    /// 차원 제약 (축 범위 등)
    Dimensional,

    /// 토폴로지 제약 (연결성 등)
    Topological,

    /// 대수적 제약 (수학적 관계)
    Algebraic,

    /// 논리적 제약 (불린 조건)
    Logical,

    /// 물리적 제약 (보존 법칙 등)
    Physical,
}

/// 제약 적용 범위
#[derive(Clone, Debug, PartialEq)]
pub enum ConstraintScope {
    Global,                         // 전체 Scheme
    Local(SegmentId),               // 특정 Segment 주변
    Regional(Vec<SegmentId>),       // 지역적
    Dimensional(usize),             // 특정 차원
    Relational(StructuralRelation), // 특정 관계 유형
}

// ==================== OBSERVATION RULES ====================

/// 관찰 규칙 - Scheme 수준의 관찰 의미론
#[derive(Clone, Debug)]
pub struct ObservationRules {
    /// 다중 가능 구성 해결 전략
    pub resolution: ResolutionStrategy,

    /// 관찰 트리거 조건
    pub triggers: Vec<ObservationTrigger>,

    /// 관찰 우선순위
    pub priority: ObservationPriority,

    /// 관찰 컨텍스트
    pub context: ObservationContext,
}

/// 해결 전략
#[derive(Clone, Debug, PartialEq)]
pub enum ResolutionStrategy {
    /// 결정론적 선택 (고정 알고리즘)
    Deterministic {
        algorithm: String,
        parameters: HashMap<String, String>,
    },

    /// 확률적 선택 (가중치 기반)
    Probabilistic {
        distribution: String,     // "uniform", "weighted", "boltzmann"
        temperature: Option<f64>, // 볼츠만 분포용
    },

    /// 에너지 최소화
    EnergyMinimization {
        energy_function: String,
        optimization_method: String,
    },

    /// 엔트로피 최대화
    EntropyMaximization,

    /// 외부 리졸버 (런타임 결정)
    External { resolver_id: String },
}

/// 관찰 트리거
#[derive(Clone, Debug, PartialEq)]
pub enum ObservationTrigger {
    OnDemand,                           // 명시적 요청 시
    Periodic { interval: u64 },         // 주기적
    Threshold { value: f64 },           // 임계값 도달 시
    StructuralChange,                   // 구조 변화 시
    DependencySatisfied,                // 의존성 충족 시
    ExternalEvent { event_id: String }, // 외부 이벤트
}

/// 관찰 우선순위
#[derive(Clone, Debug, PartialEq)]
pub enum ObservationPriority {
    Critical,   // 즉시 관찰 필요
    High,       // 높은 우선순위
    Normal,     // 일반
    Low,        // 낮은 우선순위
    Background, // 백그라운드
}

/// 관찰 컨텍스트
#[derive(Clone, Debug, Default)]
pub struct ObservationContext {
    /// 허용된 관찰자 목록 (없으면 모두 허용)
    pub allowed_observers: Option<HashSet<String>>,

    /// 관찰 제한 조건
    pub constraints: Vec<String>,

    /// 관찰 메타데이터
    pub metadata: HashMap<String, String>,
}

// ==================== MEMORY LAYOUT ABSTRACTION ====================

/// 메모리 레이아웃 추상화 - 물리적 구현 없이 논리적 매핑만 정의
#[derive(Clone, Debug)]
pub struct MemoryLayout {
    /// 레이아웃 유형
    pub layout_type: LayoutType,

    /// 매핑 함수 (좌표 → 논리적 주소)
    pub mapping: Arc<dyn Fn(&SpaceCoordinates) -> Option<LogicalAddress> + Send + Sync>,

    /// 레이아웃 메타데이터
    pub metadata: HashMap<String, String>,
}

/// 논리적 주소 (물리적 주소와 독립적)
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct LogicalAddress {
    /// 주소 공간 ID (다중 주소 공간 지원)
    pub space_id: u64,

    /// 공간 내 오프셋
    pub offset: u64,

    /// 주소 메타데이터
    pub metadata: HashMap<String, String>,
}

/// 레이아웃 유형
#[derive(Clone, Debug, PartialEq)]
pub enum LayoutType {
    /// 선형 레이아웃
    Linear,

    /// 행 우선 (2D 그리드)
    RowMajor,

    /// 열 우선
    ColumnMajor,

    /// 공간 채움 곡선 (지역성 보존)
    SpaceFillingCurve(CurveType),

    /// 계층적 레이아웃
    Hierarchical,

    /// 그래프 기반 레이아웃
    GraphBased,

    /// 사용자 정의
    Custom(String),
}

/// 공간 채움 곡선 유형
#[derive(Clone, Debug, PartialEq)]
pub enum CurveType {
    ZOrder,      // Z-order (Morton)
    Hilbert,     // Hilbert curve
    Gray,        // Gray code
    Peano,       // Peano curve
    CustomOrder, // 사용자 정의
}

// ==================== SCHEME CORE ====================

/// Scheme - 구조적 청사진 (불변)
#[derive(Clone, Debug)]
pub struct Scheme {
    /// 고유 식별자
    id: SchemeId,

    /// 차원 축 정의
    axes: Vec<Axis>,

    /// 포함된 Segment들
    segments: HashMap<SegmentId, Segment>,

    /// 구조적 관계 그래프
    relations: RelationGraph,

    /// 구조적 제약
    structural_constraints: Vec<StructuralConstraint>,

    /// 메모리 레이아웃 추상화
    memory_layout: MemoryLayout,

    /// 관찰 규칙
    observation_rules: ObservationRules,

    /// Scheme 메타데이터
    metadata: HashMap<String, String>,
}

/// 관계 그래프
#[derive(Clone, Debug, Default)]
pub struct RelationGraph {
    /// Segment → 관계 목록
    outgoing: HashMap<SegmentId, Vec<(SegmentId, StructuralRelation)>>,

    /// Segment ← 관계 목록 (역방향)
    incoming: HashMap<SegmentId, Vec<(SegmentId, StructuralRelation)>>,
}

impl RelationGraph {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_relation(&mut self, from: SegmentId, to: SegmentId, relation: StructuralRelation) {
        self.outgoing
            .entry(from)
            .or_default()
            .push((to, relation.clone()));
        self.incoming.entry(to).or_default().push((from, relation));
    }

    pub fn get_outgoing(&self, from: &SegmentId) -> Vec<(SegmentId, StructuralRelation)> {
        self.outgoing.get(from).cloned().unwrap_or_default()
    }

    pub fn get_incoming(&self, to: &SegmentId) -> Vec<(SegmentId, StructuralRelation)> {
        self.incoming.get(to).cloned().unwrap_or_default()
    }

    pub fn get_relations_between(
        &self,
        from: &SegmentId,
        to: &SegmentId,
    ) -> Vec<StructuralRelation> {
        self.outgoing
            .get(from)
            .iter()
            .flat_map(|v| v.iter())
            .filter(|(id, _)| id == to)
            .map(|(_, r)| r.clone())
            .collect()
    }
}

impl Scheme {
    /// Scheme 생성 (빌더 사용 권장)
    pub fn new(builder: SchemeBuilder) -> Self {
        let mut hasher = blake3::Hasher::new();

        // 구조적 속성 해싱 (불변성 보장)
        builder.compute_hash(&mut hasher);

        let id = SchemeId(hasher.finalize().into());

        Self {
            id,
            axes: builder.axes,
            segments: builder.segments,
            relations: builder.relations,
            structural_constraints: builder.structural_constraints,
            memory_layout: builder.memory_layout,
            observation_rules: builder.observation_rules,
            metadata: builder.metadata,
        }
    }

    pub fn id(&self) -> &SchemeId {
        &self.id
    }

    pub fn axes(&self) -> &[Axis] {
        &self.axes
    }

    pub fn dimensionality(&self) -> usize {
        self.axes.len()
    }

    pub fn contains_segment(&self, segment_id: &SegmentId) -> bool {
        self.segments.contains_key(segment_id)
    }

    pub fn get_segment(&self, segment_id: &SegmentId) -> Option<&Segment> {
        self.segments.get(segment_id)
    }

    pub fn segments(&self) -> impl Iterator<Item = &Segment> {
        self.segments.values()
    }

    pub fn segment_ids(&self) -> impl Iterator<Item = &SegmentId> {
        self.segments.keys()
    }

    /// 구조적 관계 기반 이웃 조회
    pub fn structural_neighbors(
        &self,
        segment_id: &SegmentId,
        relation_filter: Option<&str>,
    ) -> Vec<(SegmentId, StructuralRelation)> {
        self.relations
            .get_outgoing(segment_id)
            .into_iter()
            .filter(|(_, relation)| {
                relation_filter.map_or(true, |filter| match relation {
                    StructuralRelation::Adjacency { relation_type, .. } => {
                        format!("{:?}", relation_type).contains(filter)
                    }
                    StructuralRelation::Custom { name, .. } => name.contains(filter),
                    _ => true,
                })
            })
            .collect()
    }

    /// 구조적 제약 검증
    pub fn validate_structure(&self, coords: &SpaceCoordinates) -> Result<(), String> {
        for constraint in &self.structural_constraints {
            if !constraint.constraint.allows(coords) {
                return Err(format!(
                    "Structural constraint violation: {:?}",
                    constraint.constraint_type
                ));
            }
        }
        Ok(())
    }

    /// 논리적 주소 매핑 (물리적 주소 아님)
    pub fn map_to_logical_address(&self, coords: &SpaceCoordinates) -> Option<LogicalAddress> {
        (self.memory_layout.mapping)(coords)
    }

    pub fn describe(&self) -> String {
        format!(
            "Scheme {}:\n  Dimensions: {}\n  Segments: {}\n  Relations: {}\n  Constraints: {}",
            self.id.to_hex(),
            self.axes.len(),
            self.segments.len(),
            self.relations
                .outgoing
                .values()
                .map(|v| v.len())
                .sum::<usize>(),
            self.structural_constraints.len()
        )
    }
}

// ==================== SCHEME BUILDER ====================

/// Scheme 빌더 (구성 패턴)
#[derive(Default)]
pub struct SchemeBuilder {
    axes: Vec<Axis>,
    segments: HashMap<SegmentId, Segment>,
    relations: RelationGraph,
    structural_constraints: Vec<StructuralConstraint>,
    memory_layout: MemoryLayout,
    observation_rules: ObservationRules,
    metadata: HashMap<String, String>,
}

impl SchemeBuilder {
    pub fn new() -> Self {
        Self {
            memory_layout: MemoryLayout {
                layout_type: LayoutType::Linear,
                mapping: Arc::new(|coords| {
                    // 기본 선형 매핑
                    let offset = coords
                        .raw
                        .iter()
                        .map(|&v| v as u64)
                        .fold(0u64, |acc, v| acc.wrapping_mul(1009).wrapping_add(v));
                    Some(LogicalAddress {
                        space_id: 0,
                        offset,
                        metadata: HashMap::new(),
                    })
                }),
                metadata: HashMap::new(),
            },
            observation_rules: ObservationRules {
                resolution: ResolutionStrategy::Deterministic {
                    algorithm: "first-valid".to_string(),
                    parameters: HashMap::new(),
                },
                triggers: vec![ObservationTrigger::OnDemand],
                priority: ObservationPriority::Normal,
                context: ObservationContext::default(),
            },
            ..Default::default()
        }
    }

    pub fn add_axis(mut self, axis: Axis) -> Self {
        self.axes.push(axis);
        self
    }

    pub fn add_segment(mut self, segment: Segment) -> Self {
        self.segments.insert(*segment.id(), segment);
        self
    }

    pub fn add_segments<I>(mut self, segments: I) -> Self
    where
        I: IntoIterator<Item = Segment>,
    {
        for segment in segments {
            self.segments.insert(*segment.id(), segment);
        }
        self
    }

    pub fn add_relation(
        mut self,
        from: SegmentId,
        to: SegmentId,
        relation: StructuralRelation,
    ) -> Self {
        self.relations.add_relation(from, to, relation);
        self
    }

    pub fn add_structural_constraint(mut self, constraint: StructuralConstraint) -> Self {
        self.structural_constraints.push(constraint);
        self
    }

    pub fn set_memory_layout(mut self, layout: MemoryLayout) -> Self {
        self.memory_layout = layout;
        self
    }

    pub fn set_observation_rules(mut self, rules: ObservationRules) -> Self {
        self.observation_rules = rules;
        self
    }

    pub fn add_metadata(mut self, key: String, value: String) -> Self {
        self.metadata.insert(key, value);
        self
    }

    /// 해시 계산 (구조적 불변성 보장)
    fn compute_hash(&self, hasher: &mut blake3::Hasher) {
        // 축 정보 해싱
        for axis in &self.axes {
            hasher.update(axis.name.as_bytes());
            hasher.update(format!("{:?}", axis.axis_type).as_bytes());
        }

        // Segment ID 해싱 (좌표는 Segment ID에 이미 포함)
        let mut segment_ids: Vec<_> = self.segments.keys().collect();
        segment_ids.sort();
        for id in segment_ids {
            hasher.update(id.as_bytes());
        }

        // 관계 그래프 해싱
        let mut relation_entries: Vec<_> = self.relations.outgoing.iter().collect();
        relation_entries.sort_by_key(|(k, _)| *k);
        for (from_id, neighbors) in relation_entries {
            hasher.update(from_id.as_bytes());
            let mut neighbor_ids: Vec<_> = neighbors.iter().map(|(id, _)| id).collect();
            neighbor_ids.sort();
            for neighbor_id in neighbor_ids {
                hasher.update(neighbor_id.as_bytes());
            }
        }

        // 제약 조건 해싱 (타입만)
        for constraint in &self.structural_constraints {
            hasher.update(format!("{:?}", constraint.constraint_type).as_bytes());
        }
    }

    pub fn build(self) -> Scheme {
        Scheme::new(self)
    }
}

// ==================== PRE-DEFINED SCHEME TEMPLATES ====================

/// 2D 격자 Scheme 템플릿
pub mod grid2d {
    use super::*;

    pub struct Grid2DTemplate {
        width: i64,
        height: i64,
        topology: GridTopology,
    }

    impl Grid2DTemplate {
        pub fn new(width: i64, height: i64, topology: GridTopology) -> Self {
            Self {
                width,
                height,
                topology,
            }
        }

        pub fn build(self) -> Scheme {
            let mut builder = SchemeBuilder::new()
                .add_axis(Axis {
                    name: "x".to_string(),
                    axis_type: AxisType::Discrete,
                    metadata: [
                        ("range_start".to_string(), "0".to_string()),
                        ("range_end".to_string(), self.width.to_string()),
                    ]
                    .iter()
                    .cloned()
                    .collect(),
                })
                .add_axis(Axis {
                    name: "y".to_string(),
                    axis_type: AxisType::Discrete,
                    metadata: [
                        ("range_start".to_string(), "0".to_string()),
                        ("range_end".to_string(), self.height.to_string()),
                    ]
                    .iter()
                    .cloned()
                    .collect(),
                });

            // Segment 생성
            for x in 0..self.width {
                for y in 0..self.height {
                    let segment = Segment::from_values(vec![x, y]);
                    builder = builder.add_segment(segment);
                }
            }

            // 인접 관계 추가
            // (간소화: 실제로는 topology에 따라 관계 생성)
            builder = builder.add_metadata("template".to_string(), "grid2d".to_string());

            builder.build()
        }
    }
}

/// 1D 선형 Scheme 템플릿 (정수 산술)
pub mod integer_line {
    use super::*;

    pub struct IntegerLineTemplate {
        start: i64,
        end: i64,
        step: i64,
    }

    impl IntegerLineTemplate {
        pub fn new(start: i64, end: i64, step: i64) -> Self {
            Self { start, end, step }
        }

        pub fn build(self) -> Scheme {
            let mut builder = SchemeBuilder::new().add_axis(Axis {
                name: "value".to_string(),
                axis_type: AxisType::Discrete,
                metadata: [
                    ("range_start".to_string(), self.start.to_string()),
                    ("range_end".to_string(), self.end.to_string()),
                    ("step".to_string(), self.step.to_string()),
                ]
                .iter()
                .cloned()
                .collect(),
            });

            // Segment 생성
            let mut value = self.start;
            while value <= self.end {
                let segment = Segment::from_value(value);
                builder = builder.add_segment(segment);
                value += self.step;
            }

            // 인접 관계 (선형)
            // (간소화: 실제로는 이웃 관계 추가)

            builder = builder.add_metadata("template".to_string(), "integer_line".to_string());

            builder.build()
        }
    }
}

/// 그래프 기반 Scheme 템플릿
pub mod graph {
    use super::*;

    pub struct GraphTemplate {
        nodes: Vec<Vec<i64>>,            // 노드 좌표
        edges: Vec<(usize, usize, f64)>, // (from_idx, to_idx, weight)
    }

    impl GraphTemplate {
        pub fn new(nodes: Vec<Vec<i64>>, edges: Vec<(usize, usize, f64)>) -> Self {
            Self { nodes, edges }
        }

        pub fn build(self) -> Scheme {
            let mut builder = SchemeBuilder::new();

            // 차원 축 (가변 길이)
            for i in 0..self.nodes[0].len() {
                builder = builder.add_axis(Axis {
                    name: format!("dim_{}", i),
                    axis_type: AxisType::Discrete,
                    metadata: HashMap::new(),
                });
            }

            // 노드 Segment 생성
            let segments: Vec<Segment> = self
                .nodes
                .iter()
                .map(|coords| Segment::from_values(coords.clone()))
                .collect();

            builder = builder.add_segments(segments.clone());

            // 간선 관계 추가
            for (from_idx, to_idx, weight) in self.edges {
                if let (Some(from_seg), Some(to_seg)) =
                    (segments.get(from_idx), segments.get(to_idx))
                {
                    builder = builder.add_relation(
                        *from_seg.id(),
                        *to_seg.id(),
                        StructuralRelation::Adjacency {
                            relation_type: AdjacencyType::Graph,
                            weight: Some(weight),
                            metadata: [("edge_type".to_string(), "directed".to_string())]
                                .iter()
                                .cloned()
                                .collect(),
                        },
                    );
                }
            }

            builder = builder.add_metadata("template".to_string(), "graph".to_string());

            builder.build()
        }
    }
}
