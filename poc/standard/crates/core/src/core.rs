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
pub struct Coordinates {
    pub raw: Vec<i64>,
}

/// Type alias for the refactored name.
pub type SpaceCoordinates = Coordinates;

impl Coordinates {
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
    coords: Coordinates,
    id: SegmentId,
}

/// Compute SegmentId from coordinates (public helper function).
pub fn segment_id_from_coords(coords: &Coordinates) -> SegmentId {
    let mut hasher = blake3::Hasher::new();
    for v in coords.raw.iter() {
        hasher.update(&v.to_le_bytes());
    }
    SegmentId(hasher.finalize().into())
}

impl Segment {
    /// Create a new Segment from coordinates.
    /// The cryptographic identity is automatically derived from the coordinates.
    pub fn new(coords: Coordinates) -> Self {
        let id = segment_id_from_coords(&coords);
        Self { coords, id }
    }

    /// Get the coordinates of this segment.
    pub fn coordinates(&self) -> &Coordinates {
        &self.coords
    }

    /// Get the cryptographic identity of this segment.
    pub fn id(&self) -> &SegmentId {
        &self.id
    }

    /// Create a Segment from a single value (convenience for 1D spaces).
    pub fn from_value(value: i64) -> Self {
        Self::new(Coordinates::new(vec![value]))
    }

    /// Create a Segment from multiple values.
    pub fn from_values(values: Vec<i64>) -> Self {
        Self::new(Coordinates::new(values))
    }
}

/// A constraint on coordinates.
pub trait Constraint: Debug + Send + Sync {
    fn allows(&self, coords: &Coordinates) -> bool;
    fn describe(&self) -> String;
}

/// A set of constraints, used by the Field.
#[derive(Debug, Default)]
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

    pub fn allows(&self, coords: &Coordinates) -> bool {
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

    /// Remove the constraint at the given index. Returns true if removed.
    pub fn remove(&mut self, index: usize) -> bool {
        if index < self.constraints.len() {
            self.constraints.remove(index);
            true
        } else {
            false
        }
    }

    /// Remove all constraints.
    pub fn clear(&mut self) {
        self.constraints.clear();
    }

    /// Number of constraints currently set.
    pub fn len(&self) -> usize {
        self.constraints.len()
    }

    /// Returns true if no constraints are set.
    pub fn is_empty(&self) -> bool {
        self.constraints.is_empty()
    }
}

/// Relational topology of the Field – currently a weighted directed graph.
/// This is one possible representation; it may be generalised later.
/// Uses SegmentId for relationship definitions to align with SSCCS cryptographic identity system.
#[derive(Debug, Default)]
pub struct TransitionMatrix {
    /// from SegmentId → [(to SegmentId, weight)]
    edges: HashMap<SegmentId, Vec<(SegmentId, f64)>>,
}

impl TransitionMatrix {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a transition using SegmentIds.
    pub fn add(&mut self, from: SegmentId, to: SegmentId, weight: f64) {
        self.edges.entry(from).or_default().push((to, weight));
    }

    /// Get transition targets from a SegmentId.
    pub fn transitions_from(&self, from: &SegmentId) -> Vec<SegmentId> {
        self.edges
            .get(from)
            .map(|v| v.iter().map(|(to, _)| *to).collect())
            .unwrap_or_default()
    }

    /// Get weight between SegmentIds.
    pub fn get_weight(&self, from: &SegmentId, to: &SegmentId) -> Option<f64> {
        self.edges
            .get(from)
            .and_then(|vec| vec.iter().find(|(t, _)| t == to).map(|(_, w)| *w))
    }
}

/// The mutable substrate of computation. Holds constraints and relational topology.
/// Does **not** own any SchemaSegment.
#[derive(Debug, Default)]
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
    /// Converts coordinates to SegmentIds internally.
    pub fn add_transition(&mut self, from: SpaceCoordinates, to: SpaceCoordinates, weight: f64) {
        let from_id = segment_id_from_coords(&from);
        let to_id = segment_id_from_coords(&to);
        self.transitions.add(from_id, to_id, weight);
    }

    /// Check whether a coordinate is allowed by all current constraints.
    pub fn allows(&self, coords: &Coordinates) -> bool {
        self.constraints.allows(coords)
    }

    /// Return all transition target SegmentIds from a given coordinate (defined by the field only).
    pub fn transition_targets(&self, from: &SpaceCoordinates) -> Vec<SegmentId> {
        let from_id = segment_id_from_coords(from);
        self.transitions.transitions_from(&from_id)
    }

    /// Describe the current constraints (for debugging).
    pub fn describe_constraints(&self) -> String {
        self.constraints.describe()
    }

    /// Remove a constraint by index. Returns true if removed.
    pub fn remove_constraint(&mut self, index: usize) -> bool {
        self.constraints.remove(index)
    }

    /// Remove all constraints from this Field.
    pub fn clear_constraints(&mut self) {
        self.constraints.clear();
    }

    /// Number of constraints currently applied to this Field.
    pub fn num_constraints(&self) -> usize {
        self.constraints.len()
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
    fn possible_next_coordinates(&self, _: &Coordinates) -> Vec<Coordinates> {
        Vec::new()
    }
}
