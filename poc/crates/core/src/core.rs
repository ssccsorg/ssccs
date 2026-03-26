//! SSCCS Proof of Concept – Core Library
//!
//! This crate provides the fundamental building blocks of the SSCCS paradigm:
//! - Immutable `SchemaSegment`
//! - Mutable `Field` (constraints + relational topology)
//! - `Projector` trait for semantic interpretation
//! - Observation functions that combine segment and field

use std::collections::HashMap;
use std::fmt::Debug;
use std::hash::Hash;
use std::sync::Arc;

// ==================== CORE TYPES ====================

/// A coordinate in an abstract space. All axes are equivalent.
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

/// Cryptographic identifier of a SchemaSegment.
/// Derived from the segment's intrinsic properties (coordinates only, since adjacency is now external).
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct SegmentId([u8; 32]);

impl PartialOrd for SegmentId {
    fn partial_cmp(&self, other: &Self) -> Option<std::cmp::Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for SegmentId {
    fn cmp(&self, other: &Self) -> std::cmp::Ordering {
        self.0.cmp(&other.0)
    }
}

impl SegmentId {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

/// An immutable point in possibility space.
/// Contains only coordinates and a cryptographic identity.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct Segment {
    coords: SpaceCoordinates,
    id: SegmentId,
}

/// Compute SegmentId from coordinates (public helper function).
pub fn segment_id_from_coords(coords: &SpaceCoordinates) -> SegmentId {
    let mut hasher = blake3::Hasher::new();
    for v in coords.raw.iter() {
        hasher.update(&v.to_le_bytes());
    }
    SegmentId(hasher.finalize().into())
}

impl Segment {
    /// Create a new Segment from coordinates.
    /// The cryptographic identity is automatically derived from the coordinates.
    pub fn new(coords: SpaceCoordinates) -> Self {
        let id = segment_id_from_coords(&coords);
        Self { coords, id }
    }

    /// Get the coordinates of this segment.
    pub fn coordinates(&self) -> &SpaceCoordinates {
        &self.coords
    }

    /// Get the cryptographic identity of this segment.
    pub fn id(&self) -> &SegmentId {
        &self.id
    }

    /// Create a Segment from a single value (convenience for 1D spaces).
    pub fn from_value(value: i64) -> Self {
        Self::new(SpaceCoordinates::new(vec![value]))
    }

    /// Create a Segment from multiple values.
    pub fn from_values(values: Vec<i64>) -> Self {
        Self::new(SpaceCoordinates::new(values))
    }
}

/// A constraint on coordinates.
pub trait Constraint: Debug + Send + Sync {
    fn allows(&self, coords: &SpaceCoordinates) -> bool;
    fn describe(&self) -> String;
}

/// A set of constraints, used by the Field.
#[derive(Debug, Clone, Default)]
pub struct ConstraintSet {
    constraints: Vec<Arc<dyn Constraint>>,
}

impl ConstraintSet {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add(&mut self, constraint: impl Constraint + 'static) {
        self.constraints.push(Arc::new(constraint));
    }

    pub fn allows(&self, coords: &SpaceCoordinates) -> bool {
        self.constraints.iter().all(|c| c.allows(coords))
    }

    pub fn describe(&self) -> String {
        if self.constraints.is_empty() {
            "no constraints".into()
        } else {
            self.constraints
                .iter()
                .map(|c| c.describe())
                .collect::<Vec<_>>()
                .join(", ")
        }
    }
}

/// Relational topology of the Field – currently a weighted directed graph.
/// This is one possible representation; it may be generalised later.
/// Uses SegmentId for relationship definitions to align with SSCCS cryptographic identity system.
#[derive(Debug, Clone, Default)]
pub struct TransitionMatrix {
    /// from SegmentId → [(to SegmentId, weight)]
    edges: HashMap<SegmentId, Vec<(SegmentId, f64)>>,
    /// Mapping from SegmentId to coordinates (for legacy API support)
    id_to_coords: HashMap<SegmentId, SpaceCoordinates>,
}

impl TransitionMatrix {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a transition using SegmentIds (new preferred API).
    /// Note: You must also store coordinates if you want to use legacy API later.
    pub fn add_by_id(
        &mut self,
        from: SegmentId,
        to: SegmentId,
        weight: f64,
        from_coords: Option<SpaceCoordinates>,
        to_coords: Option<SpaceCoordinates>,
    ) {
        self.edges.entry(from).or_default().push((to, weight));
        if let Some(coords) = from_coords {
            self.id_to_coords.insert(from, coords);
        }
        if let Some(coords) = to_coords {
            self.id_to_coords.insert(to, coords);
        }
    }

    /// Add a transition using coordinates (legacy API, converts to SegmentId internally).
    pub fn add(&mut self, from: SpaceCoordinates, to: SpaceCoordinates, weight: f64) {
        let from_id = segment_id_from_coords(&from);
        let to_id = segment_id_from_coords(&to);

        // Store coordinates for later lookup
        self.id_to_coords.insert(from_id, from.clone());
        self.id_to_coords.insert(to_id, to.clone());

        self.edges.entry(from_id).or_default().push((to_id, weight));
    }

    /// Get transition targets from a SegmentId (new preferred API).
    pub fn transitions_from_id(&self, from: &SegmentId) -> Vec<SegmentId> {
        self.edges
            .get(from)
            .map(|v| v.iter().map(|(to, _)| *to).collect())
            .unwrap_or_default()
    }

    /// Get transition targets from coordinates (legacy API).
    pub fn transitions_from(&self, from: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        let from_id = segment_id_from_coords(from);
        self.transitions_from_id(&from_id)
            .into_iter()
            .filter_map(|segment_id| self.id_to_coords.get(&segment_id).cloned())
            .collect()
    }

    /// Get weight between SegmentIds (new API).
    pub fn get_weight_by_id(&self, from: &SegmentId, to: &SegmentId) -> Option<f64> {
        self.edges
            .get(from)
            .and_then(|vec| vec.iter().find(|(t, _)| t == to).map(|(_, w)| *w))
    }

    /// Get weight between coordinates (legacy API).
    pub fn get_weight(&self, from: &SpaceCoordinates, to: &SpaceCoordinates) -> Option<f64> {
        let from_id = segment_id_from_coords(from);
        let to_id = segment_id_from_coords(to);
        self.get_weight_by_id(&from_id, &to_id)
    }
}

/// The mutable substrate of computation. Holds constraints and relational topology.
/// Does **not** own any SchemaSegment.
#[derive(Debug, Clone, Default)]
pub struct Field {
    constraints: ConstraintSet,
    transitions: TransitionMatrix,
}

impl Field {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a constraint to the field.
    pub fn add_constraint(&mut self, constraint: impl Constraint + 'static) {
        self.constraints.add(constraint);
    }

    /// Add a transition rule (from → to with weight).
    pub fn add_transition(&mut self, from: SpaceCoordinates, to: SpaceCoordinates, weight: f64) {
        self.transitions.add(from, to, weight);
    }

    /// Check whether a coordinate is allowed by all current constraints.
    pub fn allows(&self, coords: &SpaceCoordinates) -> bool {
        self.constraints.allows(coords)
    }

    /// Return all transition targets from a given coordinate (defined by the field only).
    pub fn transition_targets(&self, from: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        self.transitions.transitions_from(from)
    }

    /// Describe the current constraints (for debugging).
    pub fn describe_constraints(&self) -> String {
        self.constraints.describe()
    }
}

/// A projector gives semantic meang to a combination of Field and Segment.
/// The output is the "collapsed cross‑section" of the constraint space at that point.
pub trait Projector: Debug + Send + Sync {
    type Output: Clone + Debug + PartialEq + Eq + Hash;

    /// Produce a projection, if possible. The projector may use both the field's constraints
    /// and the segment's intrinsic properties.
    fn project(&self, field: &Field, segment: &Segment) -> Option<Self::Output>;

    /// Given a coordinate, return the possible next coordinates according to this projector's interpretation.
    /// This is where the projector defines the "adjacency" semantics (e.g., arithmetic operations, graph edges, etc.).
    /// The default implementation returns an empty vector, meaning no intrinsic adjacency.
    fn possible_next_coordinates(&self, _: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        Vec::new()
    }
}
