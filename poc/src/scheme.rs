// qs-core/poc/src/scheme.rs
use crate::core::{Constraint, Segment, SegmentId, SpaceCoordinates};
use std::collections::HashMap;
use std::fmt::Debug;
use std::hash::Hash;
use std::sync::Arc;

// ==================== SCHEME LAYER ====================

/// Cryptographic identifier of a Scheme.
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct SchemeId([u8; 32]);

impl SchemeId {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

/// Axis definition with metadata for a dimensional axis
#[derive(Clone, Debug, PartialEq)]
pub struct Axis {
    pub name: String,
    pub dimension_type: DimensionType,
    pub range: Option<(i64, i64)>, // Optional bounds
}

#[derive(Clone, Debug, PartialEq)]
pub enum DimensionType {
    Continuous,
    Discrete,
    Cyclic(Option<i64>), // Period for cyclic dimensions
    Categorical(Vec<String>),
}

impl DimensionType {
    fn as_u8(&self) -> u8 {
        match self {
            DimensionType::Continuous => 0,
            DimensionType::Discrete => 1,
            DimensionType::Cyclic(_) => 2,
            DimensionType::Categorical(_) => 3,
        }
    }
}

/// Adjacency relation between Segments
#[derive(Clone)]
pub enum AdjacencyRelation {
    Euclidean(f64),              // Distance threshold
    Manhattan(i64),              // L1 distance threshold
    GridNeighbor(GridDirection), // Grid adjacency
    Custom(Arc<dyn Fn(&SpaceCoordinates, &SpaceCoordinates) -> bool + Send + Sync>),
}

impl Debug for AdjacencyRelation {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            AdjacencyRelation::Euclidean(dist) => write!(f, "Euclidean({})", dist),
            AdjacencyRelation::Manhattan(dist) => write!(f, "Manhattan({})", dist),
            AdjacencyRelation::GridNeighbor(dir) => write!(f, "GridNeighbor({:?})", dir),
            AdjacencyRelation::Custom(_) => write!(f, "Custom(closure)"),
        }
    }
}

impl PartialEq for AdjacencyRelation {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (AdjacencyRelation::Euclidean(a), AdjacencyRelation::Euclidean(b)) => a == b,
            (AdjacencyRelation::Manhattan(a), AdjacencyRelation::Manhattan(b)) => a == b,
            (AdjacencyRelation::GridNeighbor(a), AdjacencyRelation::GridNeighbor(b)) => a == b,
            // Custom closures are never equal to each other
            _ => false,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum GridDirection {
    FourConnected,  // Up, down, left, right
    EightConnected, // Includes diagonals
    Hexagonal,      // Hex grid adjacency
}

/// Memory layout specification
#[derive(Clone)]
pub enum MemoryLayout {
    Linear,   // Simple linear mapping
    RowMajor, // For grids
    ColumnMajor,
    ZOrderCurve,  // Morton order for spatial locality
    HilbertCurve, // Better spatial locality preservation
    Custom(Arc<dyn Fn(&SpaceCoordinates) -> usize + Send + Sync>),
}

impl Debug for MemoryLayout {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            MemoryLayout::Linear => write!(f, "Linear"),
            MemoryLayout::RowMajor => write!(f, "RowMajor"),
            MemoryLayout::ColumnMajor => write!(f, "ColumnMajor"),
            MemoryLayout::ZOrderCurve => write!(f, "ZOrderCurve"),
            MemoryLayout::HilbertCurve => write!(f, "HilbertCurve"),
            MemoryLayout::Custom(_) => write!(f, "Custom(closure)"),
        }
    }
}

impl PartialEq for MemoryLayout {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (MemoryLayout::Linear, MemoryLayout::Linear) => true,
            (MemoryLayout::RowMajor, MemoryLayout::RowMajor) => true,
            (MemoryLayout::ColumnMajor, MemoryLayout::ColumnMajor) => true,
            (MemoryLayout::ZOrderCurve, MemoryLayout::ZOrderCurve) => true,
            (MemoryLayout::HilbertCurve, MemoryLayout::HilbertCurve) => true,
            // Custom closures are never equal to each other
            _ => false,
        }
    }
}

impl Default for MemoryLayout {
    fn default() -> Self {
        MemoryLayout::Linear
    }
}

/// Immutable structural blueprint
#[derive(Clone, Debug)]
pub struct Scheme {
    id: SchemeId,
    axes: Vec<Axis>,
    segments: HashMap<SegmentId, Segment>, // Segments in this scheme
    adjacency_matrix: AdjacencyMatrix,
    structural_constraints: Vec<Arc<dyn Constraint>>,
    memory_layout: MemoryLayout,
    observation_rules: ObservationRules,
    metadata: HashMap<String, String>,
}

#[derive(Clone, Debug, Default)]
pub struct AdjacencyMatrix {
    /// SegmentId -> Vec<(neighbor SegmentId, relation)>
    neighbors: HashMap<SegmentId, Vec<(SegmentId, AdjacencyRelation)>>,
}

impl AdjacencyMatrix {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_neighbor(&mut self, from: SegmentId, to: SegmentId, relation: AdjacencyRelation) {
        self.neighbors.entry(from).or_default().push((to, relation));
    }

    pub fn get_neighbors(&self, segment_id: &SegmentId) -> Vec<SegmentId> {
        self.neighbors
            .get(segment_id)
            .map(|v| v.iter().map(|(id, _)| *id).collect())
            .unwrap_or_default()
    }

    pub fn get_relation(&self, from: &SegmentId, to: &SegmentId) -> Option<AdjacencyRelation> {
        self.neighbors
            .get(from)
            .and_then(|v| v.iter().find(|(id, _)| id == to).map(|(_, r)| r.clone()))
    }
}

#[derive(Clone, Debug)]
pub struct ObservationRules {
    /// How to resolve multiple admissible configurations
    resolution_strategy: ResolutionStrategy,
    /// Observation triggers (when to observe)
    triggers: Vec<ObservationTrigger>,
    /// Projection output format
    projection_format: ProjectionFormat,
}

impl Default for ObservationRules {
    fn default() -> Self {
        Self {
            resolution_strategy: ResolutionStrategy::FirstValid,
            triggers: vec![ObservationTrigger::OnDemand],
            projection_format: ProjectionFormat::Coordinates,
        }
    }
}

#[derive(Clone)]
pub enum ResolutionStrategy {
    Deterministic(String), // Name/description of deterministic method
    WeightedRandom,        // Weighted random selection
    FirstValid,            // First admissible configuration
    MinimizeEnergy,        // Select configuration minimizing energy
    MaximizeEntropy,       // Select configuration maximizing entropy
    Custom(Arc<dyn Fn(&[SpaceCoordinates]) -> Option<SpaceCoordinates> + Send + Sync>),
}

impl Debug for ResolutionStrategy {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ResolutionStrategy::Deterministic(name) => write!(f, "Deterministic({})", name),
            ResolutionStrategy::WeightedRandom => write!(f, "WeightedRandom"),
            ResolutionStrategy::FirstValid => write!(f, "FirstValid"),
            ResolutionStrategy::MinimizeEnergy => write!(f, "MinimizeEnergy"),
            ResolutionStrategy::MaximizeEntropy => write!(f, "MaximizeEntropy"),
            ResolutionStrategy::Custom(_) => write!(f, "Custom(closure)"),
        }
    }
}

impl PartialEq for ResolutionStrategy {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ResolutionStrategy::Deterministic(a), ResolutionStrategy::Deterministic(b)) => a == b,
            (ResolutionStrategy::WeightedRandom, ResolutionStrategy::WeightedRandom) => true,
            (ResolutionStrategy::FirstValid, ResolutionStrategy::FirstValid) => true,
            (ResolutionStrategy::MinimizeEnergy, ResolutionStrategy::MinimizeEnergy) => true,
            (ResolutionStrategy::MaximizeEntropy, ResolutionStrategy::MaximizeEntropy) => true,
            // Custom closures are never equal to each other
            _ => false,
        }
    }
}

#[derive(Clone, Debug, PartialEq)]
pub enum ObservationTrigger {
    OnDemand,              // When explicitly called
    Periodic(u64),         // Every N time units
    Threshold(f64),        // When constraint satisfaction crosses threshold
    StructuralChange,      // When structure changes
    ExternalEvent(String), // On external signal
}

#[derive(Clone)]
pub enum ProjectionFormat {
    Coordinates,            // Just return coordinates
    SegmentIds,             // Return segment IDs
    StructuredData(String), // Structured data format (JSON, etc.)
    Custom(Arc<dyn Fn(&[Segment]) -> Vec<u8> + Send + Sync>),
}

impl Debug for ProjectionFormat {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ProjectionFormat::Coordinates => write!(f, "Coordinates"),
            ProjectionFormat::SegmentIds => write!(f, "SegmentIds"),
            ProjectionFormat::StructuredData(format) => write!(f, "StructuredData({})", format),
            ProjectionFormat::Custom(_) => write!(f, "Custom(closure)"),
        }
    }
}

impl PartialEq for ProjectionFormat {
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (ProjectionFormat::Coordinates, ProjectionFormat::Coordinates) => true,
            (ProjectionFormat::SegmentIds, ProjectionFormat::SegmentIds) => true,
            (ProjectionFormat::StructuredData(a), ProjectionFormat::StructuredData(b)) => a == b,
            // Custom closures are never equal to each other
            _ => false,
        }
    }
}

impl Scheme {
    /// Create a new Scheme from a builder
    pub fn new(builder: SchemeBuilder) -> Self {
        let mut hasher = blake3::Hasher::new();

        // Include all structural information in the hash
        for axis in &builder.axes {
            hasher.update(axis.name.as_bytes());
            hasher.update(&[axis.dimension_type.as_u8()]);
        }

        // Hash segment IDs (but not coordinates - those are in segment IDs)
        let mut segment_ids: Vec<_> = builder.segments.keys().collect();
        segment_ids.sort(); // Ensure deterministic ordering
        for id in segment_ids {
            hasher.update(id.as_bytes());
        }

        // Hash adjacency matrix
        let mut adjacency_entries: Vec<_> = builder.adjacency_matrix.neighbors.iter().collect();
        adjacency_entries.sort_by_key(|(k, _)| *k);
        for (from_id, neighbors) in adjacency_entries {
            hasher.update(from_id.as_bytes());
            let mut neighbor_ids: Vec<_> = neighbors.iter().map(|(id, _)| id).collect();
            neighbor_ids.sort();
            for neighbor_id in neighbor_ids {
                hasher.update(neighbor_id.as_bytes());
            }
        }

        let id = SchemeId(hasher.finalize().into());

        Self {
            id,
            axes: builder.axes,
            segments: builder.segments,
            adjacency_matrix: builder.adjacency_matrix,
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

    pub fn neighbors_of(&self, segment_id: &SegmentId) -> Vec<SegmentId> {
        self.adjacency_matrix.get_neighbors(segment_id)
    }

    pub fn get_adjacency_relation(
        &self,
        from: &SegmentId,
        to: &SegmentId,
    ) -> Option<AdjacencyRelation> {
        self.adjacency_matrix.get_relation(from, to)
    }

    pub fn structural_constraints_satisfied(&self, coords: &SpaceCoordinates) -> bool {
        self.structural_constraints.iter().all(|c| c.allows(coords))
    }

    pub fn map_to_memory(&self, coords: &SpaceCoordinates) -> Option<usize> {
        match &self.memory_layout {
            MemoryLayout::Linear => {
                // Simple linear mapping: sum of coordinates (scaled)
                Some(coords.raw.iter().map(|&v| v as usize).sum())
            }
            MemoryLayout::RowMajor => {
                // Row-major for 2D: address = row * width + column
                if coords.raw.len() >= 2 {
                    // Assuming axes[0] is rows, axes[1] is columns
                    let row = coords.raw[0] as usize;
                    let col = coords.raw[1] as usize;
                    // Get width from axis range or use default
                    let width = self
                        .axes
                        .get(1)
                        .and_then(|a| a.range.map(|(min, max)| (max - min + 1) as usize))
                        .unwrap_or(1024); // Default
                    Some(row * width + col)
                } else {
                    None
                }
            }
            MemoryLayout::ColumnMajor => {
                // Column-major for 2D: address = column * height + row
                if coords.raw.len() >= 2 {
                    let row = coords.raw[0] as usize;
                    let col = coords.raw[1] as usize;
                    let height = self
                        .axes
                        .get(0)
                        .and_then(|a| a.range.map(|(min, max)| (max - min + 1) as usize))
                        .unwrap_or(1024);
                    Some(col * height + row)
                } else {
                    None
                }
            }
            MemoryLayout::ZOrderCurve => {
                // Morton order (Z-order curve)
                Some(z_order_encode(&coords.raw))
            }
            MemoryLayout::HilbertCurve => {
                // Hilbert curve encoding (better locality)
                Some(hilbert_encode(&coords.raw))
            }
            MemoryLayout::Custom(func) => Some(func(coords)),
        }
    }

    pub fn describe(&self) -> String {
        format!(
            "Scheme {} with {} dimensions, {} segments, {} adjacency relations",
            hex::encode(self.id.as_bytes()),
            self.axes.len(),
            self.segments.len(),
            self.adjacency_matrix
                .neighbors
                .values()
                .map(|v| v.len())
                .sum::<usize>()
        )
    }
}

// Helper functions for space-filling curves
fn z_order_encode(coords: &[i64]) -> usize {
    let mut result = 0usize;

    // Find maximum coordinate value to determine bits needed
    let max_coord = coords.iter().map(|&v| v.abs() as u64).max().unwrap_or(0);
    let bits_needed = (max_coord as f64).log2().ceil() as usize + 1;

    for bit in 0..bits_needed {
        for (dim, &coord) in coords.iter().enumerate() {
            let bit_val = ((coord as u64 >> bit) & 1) as usize;
            result |= bit_val << (dim * bits_needed + bit);
        }
    }

    result
}

fn hilbert_encode(_coords: &[i64]) -> usize {
    // Simplified Hilbert curve encoding (2D only for now)
    // In practice, use a proper Hilbert curve library
    if _coords.len() >= 2 {
        let x = _coords[0] as u32;
        let y = _coords[1] as u32;

        // Simple interleaving for demonstration
        let mut result = 0u32;
        for i in 0..16 {
            result |= ((x >> i) & 1) << (2 * i);
            result |= ((y >> i) & 1) << (2 * i + 1);
        }
        result as usize
    } else {
        0
    }
}

/// Builder pattern for creating Schemes
#[derive(Default)]
pub struct SchemeBuilder {
    axes: Vec<Axis>,
    segments: HashMap<SegmentId, Segment>,
    adjacency_matrix: AdjacencyMatrix,
    structural_constraints: Vec<Arc<dyn Constraint>>,
    memory_layout: MemoryLayout,
    observation_rules: ObservationRules,
    metadata: HashMap<String, String>,
}

impl SchemeBuilder {
    pub fn new() -> Self {
        Self::default()
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

    pub fn add_adjacency(
        mut self,
        from: SegmentId,
        to: SegmentId,
        relation: AdjacencyRelation,
    ) -> Self {
        self.adjacency_matrix.add_neighbor(from, to, relation);
        self
    }

    pub fn add_structural_constraint(mut self, constraint: impl Constraint + 'static) -> Self {
        self.structural_constraints.push(Arc::new(constraint));
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

    pub fn build(self) -> Scheme {
        Scheme::new(self)
    }
}

// ==================== SCHEME IMPLEMENTATIONS ====================

/// A simple 2D grid scheme
pub struct Grid2DScheme {
    width: i64,
    height: i64,
    segments: HashMap<SegmentId, Segment>,
}

impl Grid2DScheme {
    pub fn new(width: i64, height: i64) -> Self {
        let mut segments = HashMap::new();

        // Create segments for each grid position
        for x in 0..width {
            for y in 0..height {
                let segment = Segment::from_values(vec![x, y]);
                segments.insert(*segment.id(), segment);
            }
        }

        Self {
            width,
            height,
            segments,
        }
    }

    pub fn to_scheme(self) -> Scheme {
        let mut builder = SchemeBuilder::new()
            .add_axis(Axis {
                name: "x".to_string(),
                dimension_type: DimensionType::Discrete,
                range: Some((0, self.width - 1)),
            })
            .add_axis(Axis {
                name: "y".to_string(),
                dimension_type: DimensionType::Discrete,
                range: Some((0, self.height - 1)),
            })
            .set_memory_layout(MemoryLayout::RowMajor)
            .set_observation_rules(ObservationRules {
                resolution_strategy: ResolutionStrategy::Deterministic("grid-nearest".to_string()),
                triggers: vec![ObservationTrigger::OnDemand],
                projection_format: ProjectionFormat::Coordinates,
            });

        // Add all segments
        builder = builder.add_segments(self.segments.into_values());

        builder.build()
    }
}

/// A 1D integer line scheme (like integer arithmetic)
pub struct IntegerLineScheme {
    start: i64,
    end: i64,
}

impl IntegerLineScheme {
    pub fn new(start: i64, end: i64) -> Self {
        Self { start, end }
    }

    pub fn to_scheme(self) -> Scheme {
        let mut builder = SchemeBuilder::new()
            .add_axis(Axis {
                name: "value".to_string(),
                dimension_type: DimensionType::Discrete,
                range: Some((self.start, self.end)),
            })
            .set_memory_layout(MemoryLayout::Linear)
            .set_observation_rules(ObservationRules {
                resolution_strategy: ResolutionStrategy::Deterministic("arithmetic".to_string()),
                triggers: vec![ObservationTrigger::OnDemand],
                projection_format: ProjectionFormat::Coordinates,
            });

        // Create segments for each integer value
        for value in self.start..=self.end {
            let segment = Segment::from_value(value);
            builder = builder.add_segment(segment);
        }

        builder.build()
    }
}
