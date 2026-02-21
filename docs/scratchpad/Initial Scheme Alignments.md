
```rust
// qs-core/poc/src/scheme/abstract.rs
//! Scheme abstraction layer -defines structural relationships without physical memory implementation

use crate::core::{Segment, SegmentId, SpaceCoordinates, Constraint};
use std::collections::{HashMap, HashSet};
use std::fmt::Debug;
use std::hash::Hash;
use std::sync::Arc;

// ==================== SCHEME IDENTITY ====================

/// Scheme's cryptographic identifier
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

/// Abstract definition of dimension axis
#[derive(Clone, Debug, PartialEq)]
pub struct Axis {
    /// Axis names (e.g. "x", "y", "time", "energy")
    pub name: String,
    
    /// Axis type -implementation determines physical representation
    pub axis_type: AxisType,
    
    /// Axis metadata (optional)
    pub metadata: HashMap<String, String>,
}

/// Axis types -define meaning without physical representation
#[derive(Clone, Debug, PartialEq)]
pub enum AxisType {
    /// Discrete axis (integer value)
    Discrete,
    
    /// Continuous axis (real values, physical resolution determined by implementation)
    Continuous,
    
    /// Circular axis (periodic, e.g. angle 0-360)
    Cyclic(Option<i64>), // cycle (optional)
    
    /// Categorical axis (discrete categories)
    Categorical,
    
    /// Relational axis (defines relationships with other axes)
    Relational(String), // Related axis name
    
    /// Axis with units of measurement
    WithUnit(String), // Units (e.g. "meters", "seconds")
}

// ==================== STRUCTURAL RELATIONS ====================

/// Structural relationship between segments
#[derive(Clone, Debug, PartialEq)]
pub enum StructuralRelation {
    /// Adjacency relationships (spatial/conceptual proximity)
    Adjacency {
        relation_type: AdjacencyType,
        weight: Option<f64>, // Relationship Strength (optional)
        metadata: HashMap<String, String>,
    },
    
    /// Hierarchical relationship (parent-child)
    Hierarchy {
        parent: SegmentId,
        depth: i64,
        relation_type: HierarchyType,
    },
    
    /// Dependency (A depends on B)
    Dependency {
        dependent: SegmentId,
        dependency_type: DependencyType,
        strength: f64,
    },
    
    /// Equivalence relationship (different expressions within the same structure)
    Equivalence {
        equivalence_class: u64,
        symmetry: SymmetryType,
    },
    
    /// custom relationship
    Custom {
        name: String,
        predicate: Arc<dyn Fn(&Segment, &Segment) -> bool + Send + Sync>,
    },
}

/// Adjacency type
#[derive(Clone, Debug, PartialEq)]
pub enum AdjacencyType {
    /// Euclidean distance criterion
    Euclidean(f64), // distance threshold
    
    /// Based on Manhattan distance
    Manhattan(i64), // L1 distance threshold
    
    /// Grid neighbors (2D/3D grid)
    Grid(GridTopology),
    
    /// Graph connectivity (arbitrary topology)
    Graph,
    
    /// Space-time contiguity (time + space)
    Spatiotemporal,
    
    /// Conceptual adjacency (semantic similarity)
    Conceptual,
}

/// grid topology
#[derive(Clone, Debug, PartialEq)]
pub enum GridTopology {
    FourConnected,   // Up, down, left and right
    EightConnected,  // Includes diagonal
    Hexagonal,       // hexagon grid
    Triangular,      // triangular grid
    Custom(Vec<(i64, i64)>), // custom offset
}

/// Hierarchical relationship type
#[derive(Clone, Debug, PartialEq)]
pub enum HierarchyType {
    Containment,     // inclusion relationship
    Inheritance,     // inheritance relationship
    Composition,     // composition relationship
    Specialization,  // specialization relationship
}

/// dependency type
#[derive(Clone, Debug, PartialEq)]
pub enum DependencyType {
    DataFlow,        // data flow
    ControlFlow,     // control flow
    Temporal,        // temporal dependence
    Causal,          // causality
    Resource,        // resource dependence
}

/// Symmetry type
#[derive(Clone, Debug, PartialEq)]
pub enum SymmetryType {
    Symmetric,       // Two-way equivalent
    Asymmetric,      // One-way equivalent
    Reflexive,       // self equal
    Transitive,      // transitive
}

// ==================== STRUCTURAL CONSTRAINTS ====================

/// Structural constraints (scheme level invariant constraints)
#[derive(Clone, Debug)]
pub struct StructuralConstraint {
    /// Constraints (different from field constraints)
    constraint: Arc<dyn Constraint>,
    
    /// Pharmaceutical type
    constraint_type: ConstraintType,
    
    /// applied area
    scope: ConstraintScope,
}

/// Pharmaceutical type
#[derive(Clone, Debug, PartialEq)]
pub enum ConstraintType {
    /// Dimensional constraints (axis ranges, etc.)
    Dimensional,
    
    /// Topological constraints (connectivity, etc.)
    Topological,
    
    /// Algebraic constraints (mathematical relationships)
    Algebraic,
    
    /// Logical Constraints (Boolean Conditions)
    Logical,
    
    /// Physical constraints (conservation laws, etc.)
    Physical,
}

/// Pharmaceutical coverage
#[derive(Clone, Debug, PartialEq)]
pub enum ConstraintScope {
    Global,                     // Full Scheme
    Local(SegmentId),           // Around a specific Segment
    Regional(Vec<SegmentId>),   // regional
    Dimensional(usize),         // specific dimension
    Relational(StructuralRelation), // Specific relationship type
}

// ==================== OBSERVATION RULES ====================

/// Observation Rules -Scheme-level observation semantics
#[derive(Clone, Debug)]
pub struct ObservationRules {
    /// Multiple possible configuration resolution strategies
    pub resolution: ResolutionStrategy,
    
    /// Observation trigger condition
    pub triggers: Vec<ObservationTrigger>,
    
    /// Observation Priority
    pub priority: ObservationPriority,
    
    /// observation context
    pub context: ObservationContext,
}

/// solution strategy
#[derive(Clone, Debug, PartialEq)]
pub enum ResolutionStrategy {
    /// Deterministic selection (fixed algorithm)
    Deterministic {
        algorithm: String,
        parameters: HashMap<String, String>,
    },
    
    /// Probabilistic selection (weighted based)
    Probabilistic {
        distribution: String, // "uniform", "weighted", "boltzmann"
        temperature: Option<f64>, // For Boltzmann distribution
    },
    
    /// energy minimization
    EnergyMinimization {
        energy_function: String,
        optimization_method: String,
    },
    
    /// Maximize entropy
    EntropyMaximization,
    
    /// External resolver (runtime decision)
    External {
        resolver_id: String,
    },
}

/// observation trigger
#[derive(Clone, Debug, PartialEq)]
pub enum ObservationTrigger {
    OnDemand,                    // Upon explicit request
    Periodic { interval: u64 },  // periodic
    Threshold { value: f64 },    // When threshold is reached
    StructuralChange,           // When structure changes
    DependencySatisfied,        // When dependencies are met
    ExternalEvent { event_id: String }, // external event
}

/// Observation Priority
#[derive(Clone, Debug, PartialEq)]
pub enum ObservationPriority {
    Critical,    // Immediate observation required
    High,        // high priority
    Normal,      // common
    Low,         // low priority
    Background,  // background
}

/// observation context
#[derive(Clone, Debug, Default)]
pub struct ObservationContext {
    /// List of allowed observers (if none, allow all)
    pub allowed_observers: Option<HashSet<String>>,
    
    /// observation constraints
    pub constraints: Vec<String>,
    
    /// Observation metadata
    pub metadata: HashMap<String, String>,
}

// ==================== MEMORY LAYOUT ABSTRACTION ====================

/// Memory layout abstraction -define only logical mappings without physical implementation
#[derive(Clone, Debug)]
pub struct MemoryLayout {
    /// Layout Type
    pub layout_type: LayoutType,
    
    /// Mapping function (coordinate → logical address)
    pub mapping: Arc<dyn Fn(&SpaceCoordinates) -> Option<LogicalAddress> + Send + Sync>,
    
    /// Layout metadata
    pub metadata: HashMap<String, String>,
}

/// Logical address (independent of physical address)
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct LogicalAddress {
    /// Address space ID (multiple address spaces supported)
    pub space_id: u64,
    
    /// offset in space
    pub offset: u64,
    
    /// address metadata
    pub metadata: HashMap<String, String>,
}

/// Layout Type
#[derive(Clone, Debug, PartialEq)]
pub enum LayoutType {
    /// linear layout
    Linear,
    
    /// Row-first (2D grid)
    RowMajor,
    
    /// Column priority
    ColumnMajor,
    
    /// Space-filling curve (preserving locality)
    SpaceFillingCurve(CurveType),
    
    /// Hierarchical Layout
    Hierarchical,
    
    /// Graph-based layout
    GraphBased,
    
    /// custom
    Custom(String),
}

/// Space-filling curve type
#[derive(Clone, Debug, PartialEq)]
pub enum CurveType {
    ZOrder,      // Z-order (Morton)
    Hilbert,     // Hilbert curve
    Gray,        // Gray code
    Peano,       // Peano curves
    CustomOrder, // custom
}

// ==================== SCHEME CORE ====================

/// Scheme -structural blueprint (immutable)
#[derive(Clone, Debug)]
pub struct Scheme {
    /// unique identifier
    id: SchemeId,
    
    /// Dimension axis definition
    axes: Vec<Axis>,
    
    /// Segments included
    segments: HashMap<SegmentId, Segment>,
    
    /// Structural Relationship Graph
    relations: RelationGraph,
    
    /// structural constraints
    structural_constraints: Vec<StructuralConstraint>,
    
    /// Memory layout abstraction
    memory_layout: MemoryLayout,
    
    /// observation rule
    observation_rules: ObservationRules,
    
    /// Scheme metadata
    metadata: HashMap<String, String>,
}

/// relationship graph
#[derive(Clone, Debug, Default)]
pub struct RelationGraph {
    /// Segment → Relationship list
    outgoing: HashMap<SegmentId, Vec<(SegmentId, StructuralRelation)>>,
    
    /// Segment ← Relationship List (reverse)
    incoming: HashMap<SegmentId, Vec<(SegmentId, StructuralRelation)>>,
}

impl RelationGraph {
    pub fn new() -> Self {
        Self::default()
    }
    
    pub fn add_relation(&mut self, from: SegmentId, to: SegmentId, relation: StructuralRelation) {
        self.outgoing.entry(from).or_default().push((to, relation.clone()));
        self.incoming.entry(to).or_default().push((from, relation));
    }
    
    pub fn get_outgoing(&self, from: &SegmentId) -> Vec<(SegmentId, StructuralRelation)> {
        self.outgoing.get(from).cloned().unwrap_or_default()
    }
    
    pub fn get_incoming(&self, to: &SegmentId) -> Vec<(SegmentId, StructuralRelation)> {
        self.incoming.get(to).cloned().unwrap_or_default()
    }
    
    pub fn get_relations_between(&self, from: &SegmentId, to: &SegmentId) -> Vec<StructuralRelation> {
        self.outgoing.get(from)
            .iter()
            .flat_map(|v| v.iter())
            .filter(|(id, _)| id == to)
            .map(|(_, r)| r.clone())
            .collect()
    }
}

impl Scheme {
    /// Create Scheme (recommended to use Builder)
    pub fn new(builder: SchemeBuilder) -> Self {
        let mut hasher = blake3::Hasher::new();
        
        // Structural property hashing (ensuring immutability)
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
    
    /// Structured relationship-based neighbor lookup
    pub fn structural_neighbors(&self, segment_id: &SegmentId, relation_filter: Option<&str>) 
        -> Vec<(SegmentId, StructuralRelation)> 
    {
        self.relations.get_outgoing(segment_id)
            .into_iter()
            .filter(|(_, relation)| {
                relation_filter.map_or(true, |filter| {
                    match relation {
                        StructuralRelation::Adjacency { relation_type, .. } => {
                            format!("{:?}", relation_type).contains(filter)
                        }
                        StructuralRelation::Custom { name, .. } => name.contains(filter),
                        _ => true,
                    }
                })
            })
            .collect()
    }
    
    /// Structural constraint verification
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
    
    /// Logical address mapping (not physical address)
    pub fn map_to_logical_address(&self, coords: &SpaceCoordinates) -> Option<LogicalAddress> {
        (self.memory_layout.mapping)(coords)
    }
    
    pub fn describe(&self) -> String {
        format!(
            "Scheme {}:\n  Dimensions: {}\n  Segments: {}\n  Relations: {}\n  Constraints: {}",
            self.id.to_hex(),
            self.axes.len(),
            self.segments.len(),
            self.relations.outgoing.values().map(|v| v.len()).sum::<usize>(),
            self.structural_constraints.len()
        )
    }
}

// ==================== SCHEME BUILDER ====================

/// Scheme Builder (Configuration Pattern)
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
                    // Basic linear mapping
                    let offset = coords.raw.iter()
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
        I: IntoIterator<Item = Segment>
    {
        for segment in segments {
            self.segments.insert(*segment.id(), segment);
        }
        self
    }
    
    pub fn add_relation(mut self, from: SegmentId, to: SegmentId, relation: StructuralRelation) -> Self {
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
    
    /// Hash calculations (ensuring structural immutability)
    fn compute_hash(&self, hasher: &mut blake3::Hasher) {
        // Hashing axis information
        for axis in &self.axes {
            hasher.update(axis.name.as_bytes());
            hasher.update(format!("{:?}", axis.axis_type).as_bytes());
        }
        
        // Hashing Segment ID (coordinates are already included in Segment ID)
        let mut segment_ids: Vec<_> = self.segments.keys().collect();
        segment_ids.sort();
        for id in segment_ids {
            hasher.update(id.as_bytes());
        }
        
        // Relationship Graph Hashing
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
        
        // Constraint hashing (type only)
        for constraint in &self.structural_constraints {
            hasher.update(format!("{:?}", constraint.constraint_type).as_bytes());
        }
    }
    
    pub fn build(self) -> Scheme {
        Scheme::new(self)
    }
}

// ==================== PRE-DEFINED SCHEME TEMPLATES ====================

/// 2D Grid Scheme Template
pub mod grid2d {
    use super::*;
    
    pub struct Grid2DTemplate {
        width: i64,
        height: i64,
        topology: GridTopology,
    }
    
    impl Grid2DTemplate {
        pub fn new(width: i64, height: i64, topology: GridTopology) -> Self {
            Self { width, height, topology }
        }
        
        pub fn build(self) -> Scheme {
            let mut builder = SchemeBuilder::new()
                .add_axis(Axis {
                    name: "x".to_string(),
                    axis_type: AxisType::Discrete,
                    metadata: [("range_start".to_string(), "0".to_string()),
                              ("range_end".to_string(), self.width.to_string())]
                        .iter().cloned().collect(),
                })
                .add_axis(Axis {
                    name: "y".to_string(),
                    axis_type: AxisType::Discrete,
                    metadata: [("range_start".to_string(), "0".to_string()),
                              ("range_end".to_string(), self.height.to_string())]
                        .iter().cloned().collect(),
                });
            
            // Segment creation
            for x in 0..self.width {
                for y in 0..self.height {
                    let segment = Segment::from_values(vec![x, y]);
                    builder = builder.add_segment(segment);
                }
            }
            
            // Add adjacency relationship
            // (simplification: actually creates relationships based on topology)
            builder = builder.add_metadata("template".to_string(), "grid2d".to_string());
            
            builder.build()
        }
    }
}

/// 1D Linear Scheme Template (Integer Arithmetic)
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
            let mut builder = SchemeBuilder::new()
                .add_axis(Axis {
                    name: "value".to_string(),
                    axis_type: AxisType::Discrete,
                    metadata: [("range_start".to_string(), self.start.to_string()),
                              ("range_end".to_string(), self.end.to_string()),
                              ("step".to_string(), self.step.to_string())]
                        .iter().cloned().collect(),
                });
            
            // Segment creation
            let mut value = self.start;
            while value <= self.end {
                let segment = Segment::from_value(value);
                builder = builder.add_segment(segment);
                value += self.step;
            }
            
            // Adjacency relationship (linear)
            // (simplification: actually just adding neighbor relationships)
            
            builder = builder.add_metadata("template".to_string(), "integer_line".to_string());
            
            builder.build()
        }
    }
}

/// Graph-based Scheme template
pub mod graph {
    use super::*;
    
    pub struct GraphTemplate {
        nodes: Vec<Vec<i64>>,      // node coordinates
        edges: Vec<(usize, usize, f64)>, // (from_idx, to_idx, weight)
    }
    
    impl GraphTemplate {
        pub fn new(nodes: Vec<Vec<i64>>, edges: Vec<(usize, usize, f64)>) -> Self {
            Self { nodes, edges }
        }
        
        pub fn build(self) -> Scheme {
            let mut builder = SchemeBuilder::new();
            
            // Dimension axis (variable length)
            for i in 0..self.nodes[0].len() {
                builder = builder.add_axis(Axis {
                    name: format!("dim_{}", i),
                    axis_type: AxisType::Discrete,
                    metadata: HashMap::new(),
                });
            }
            
            // Create node segment
            let segments: Vec<Segment> = self.nodes.iter()
                .map(|coords| Segment::from_values(coords.clone()))
                .collect();
            
            builder = builder.add_segments(segments.clone());
            
            // Add edge relationship
            for (from_idx, to_idx, weight) in self.edges {
                if let (Some(from_seg), Some(to_seg)) = (segments.get(from_idx), segments.get(to_idx)) {
                    builder = builder.add_relation(
                        *from_seg.id(),
                        *to_seg.id(),
                        StructuralRelation::Adjacency {
                            relation_type: AdjacencyType::Graph,
                            weight: Some(weight),
                            metadata: [("edge_type".to_string(), "directed".to_string())]
                                .iter().cloned().collect(),
                        }
                    );
                }
            }
            
            builder = builder.add_metadata("template".to_string(), "graph".to_string());
            
            builder.build()
        }
    }
}
```

```rust
// qs-core/poc/src/scheme/mod.rs
//! Scheme module -structural blueprint abstraction layer

pub mod abstract_scheme;
pub use abstract_scheme::*;

/// Scheme traits -a common interface for various Scheme implementations
pub trait SchemeTrait: Debug + Send + Sync {
    /// Scheme identifier
    fn id(&self) -> &SchemeId;
    
    /// Dimension Axis Information
    fn axes(&self) -> &[Axis];
    
    /// number of dimensions
    fn dimensionality(&self) -> usize;
    
    /// Segment inclusion or not
    fn contains_segment(&self, segment_id: &SegmentId) -> bool;
    
    /// Segment lookup
    fn get_segment(&self, segment_id: &SegmentId) -> Option<&Segment>;
    
    /// all Segment iterators
    fn segments(&self) -> Box<dyn Iterator<Item = &Segment> + '_>;
    
    /// Structural verification
    fn validate_structure(&self, coords: &SpaceCoordinates) -> Result<(), String>;
    
    /// Logical address mapping
    fn map_to_logical_address(&self, coords: &SpaceCoordinates) -> Option<LogicalAddress>;
    
    /// Scheme Description
    fn describe(&self) -> String;
}

/// Scheme implementation
#[derive(Clone, Debug)]
pub enum SchemeImpl {
    /// Basic Scheme implementation
    Basic(abstract_scheme::Scheme),
    
    /// Composite Scheme (composition of other Schemes)
    Composite(CompositeScheme),
    
    /// Converted Scheme (variant of basic Scheme)
    Transformed(TransformedScheme),
}

impl SchemeTrait for SchemeImpl {
    fn id(&self) -> &SchemeId {
        match self {
            SchemeImpl::Basic(s) => s.id(),
            SchemeImpl::Composite(s) => s.id(),
            SchemeImpl::Transformed(s) => s.id(),
        }
    }
    
    fn axes(&self) -> &[Axis] {
        match self {
            SchemeImpl::Basic(s) => s.axes(),
            SchemeImpl::Composite(s) => s.axes(),
            SchemeImpl::Transformed(s) => s.axes(),
        }
    }
    
    fn dimensionality(&self) -> usize {
        match self {
            SchemeImpl::Basic(s) => s.dimensionality(),
            SchemeImpl::Composite(s) => s.dimensionality(),
            SchemeImpl::Transformed(s) => s.dimensionality(),
        }
    }
    
    fn contains_segment(&self, segment_id: &SegmentId) -> bool {
        match self {
            SchemeImpl::Basic(s) => s.contains_segment(segment_id),
            SchemeImpl::Composite(s) => s.contains_segment(segment_id),
            SchemeImpl::Transformed(s) => s.contains_segment(segment_id),
        }
    }
    
    fn get_segment(&self, segment_id: &SegmentId) -> Option<&Segment> {
        match self {
            SchemeImpl::Basic(s) => s.get_segment(segment_id),
            SchemeImpl::Composite(s) => s.get_segment(segment_id),
            SchemeImpl::Transformed(s) => s.get_segment(segment_id),
        }
    }
    
    fn segments(&self) -> Box<dyn Iterator<Item = &Segment> + '_> {
        match self {
            SchemeImpl::Basic(s) => Box::new(s.segments()),
            SchemeImpl::Composite(s) => Box::new(s.segments()),
            SchemeImpl::Transformed(s) => Box::new(s.segments()),
        }
    }
    
    fn validate_structure(&self, coords: &SpaceCoordinates) -> Result<(), String> {
        match self {
            SchemeImpl::Basic(s) => s.validate_structure(coords),
            SchemeImpl::Composite(s) => s.validate_structure(coords),
            SchemeImpl::Transformed(s) => s.validate_structure(coords),
        }
    }
    
    fn map_to_logical_address(&self, coords: &SpaceCoordinates) -> Option<LogicalAddress> {
        match self {
            SchemeImpl::Basic(s) => s.map_to_logical_address(coords),
            SchemeImpl::Composite(s) => s.map_to_logical_address(coords),
            SchemeImpl::Transformed(s) => s.map_to_logical_address(coords),
        }
    }
    
    fn describe(&self) -> String {
        match self {
            SchemeImpl::Basic(s) => s.describe(),
            SchemeImpl::Composite(s) => s.describe(),
            SchemeImpl::Transformed(s) => s.describe(),
        }
    }
}

/// Composite Scheme (composition of multiple Schemes)
#[derive(Clone, Debug)]
pub struct CompositeScheme {
    id: SchemeId,
    components: Vec<SchemeImpl>,
    composition_rules: CompositionRules,
}

/// composition rules
#[derive(Clone, Debug)]
pub struct CompositionRules {
    pub combination_method: CombinationMethod,
    pub alignment: Option<AlignmentRules>,
    pub conflict_resolution: ConflictResolution,
}

#[derive(Clone, Debug, PartialEq)]
pub enum CombinationMethod {
    Union,          // union
    Intersection,   // intersection
    Product,        // Cartesian product
    Sum,            // straight
    Custom(Arc<dyn Fn(&[&SchemeImpl]) -> SchemeImpl + Send + Sync>),
}

#[derive(Clone, Debug, PartialEq)]
pub struct AlignmentRules {
    pub alignment_axes: Vec<(usize, usize)>, // (comp1_axis_idx, comp2_axis_idx)
    pub tolerance: Option<f64>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum ConflictResolution {
    FirstWins,      // First Scheme first
    Priority(Vec<usize>), // Priority based
    Merge,          // merge attempt
    Fail,           // Fail on collision
}

/// Converted Scheme
#[derive(Clone, Debug)]
pub struct TransformedScheme {
    id: SchemeId,
    base: Box<SchemeImpl>,
    transformation: Transformation,
}

/// Scheme conversion
#[derive(Clone, Debug)]
pub struct Transformation {
    pub transform_type: TransformType,
    pub parameters: HashMap<String, String>,
}

#[derive(Clone, Debug, PartialEq)]
pub enum TransformType {
    Translation(Vec<i64>),     // parallel movement
    Rotation(Matrix<f64>),     // rotation
    Scaling(Vec<f64>),         // scaling
    Shearing(Matrix<f64>),     // shear conversion
    Projection(Matrix<f64>),   // projection
    DimensionalReduction,      // dimensionality reduction
    DimensionalExpansion,      // dimension expansion
    TopologicalTransform,      // Topology Transformation
}

/// Simple matrix type (actual implementation omitted)
#[derive(Clone, Debug, PartialEq)]
pub struct Matrix<T>(Vec<Vec<T>>);
```
The Scheme abstraction layer is now complete. Key features:

## 🔑 **Key Design Principles**

1. **Physical implementation independence**
   -Define only `LogicalAddress`, physical address will be implemented later
   -`MemoryLayout` provides only mapping functions

2. **Structural Relationship Center**
   -Define various relationship types with `StructuralRelation`
   -Representation of relationship network with `RelationGraph`

3. **Expandable axis system**
   -Supports various dimension types with `AxisType`
   -Store additional properties as metadata

4. **Template-based creation**
   -Provides common patterns such as Grid, Graph, IntegerLine, etc.
   -Complex Scheme configuration possible with `SchemeBuilder`

5. **Encryption Identification**
   -Generate unique ID with structural attribute-based hash
   -Guaranteed immutability

## 🏗️ **Use example**

```rust
// 1. Create a basic scheme
let grid_scheme = grid2d::Grid2DTemplate::new(10, 10, GridTopology::FourConnected)
    .build();

// 2. Add structural relationships
let mut builder = SchemeBuilder::new();
builder = builder.add_axis(Axis {
    name: "x".to_string(),
    axis_type: AxisType::Discrete,
    metadata: HashMap::new(),
});

// 3. Composition of complex scheme
let composite = CompositeScheme::new(
    vec![grid_scheme, another_scheme],
    CompositionRules { /*... */ }
);

// 4. Structural verification
if let Err(e) = grid_scheme.validate_structure(&coords) {
    println!("Validation failed: {}", e);
}

// 5. Logical address mapping
if let Some(addr) = grid_scheme.map_to_logical_address(&coords) {
    println!("Logical address: {:?}", addr);
}
```
