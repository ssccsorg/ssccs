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

impl Segment {
    /// Create a new Segment from coordinates.
    /// The cryptographic identity is automatically derived from the coordinates.
    pub fn new(coords: SpaceCoordinates) -> Self {
        let id = Self::compute_id(&coords);
        Self { coords, id }
    }

    /// Compute the cryptographic identity from coordinates.
    fn compute_id(coords: &SpaceCoordinates) -> SegmentId {
        let mut hasher = blake3::Hasher::new();
        for v in coords.raw.iter() {
            hasher.update(&v.to_le_bytes());
        }
        SegmentId(hasher.finalize().into())
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
#[derive(Debug, Clone, Default)]
pub struct TransitionMatrix {
    /// from → [(to, weight)]
    edges: HashMap<SpaceCoordinates, Vec<(SpaceCoordinates, f64)>>,
}

impl TransitionMatrix {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add(&mut self, from: SpaceCoordinates, to: SpaceCoordinates, weight: f64) {
        self.edges.entry(from).or_default().push((to, weight));
    }

    pub fn transitions_from(&self, from: &SpaceCoordinates) -> Vec<SpaceCoordinates> {
        self.edges
            .get(from)
            .map(|v| v.iter().map(|(to, _)| to.clone()).collect())
            .unwrap_or_default()
    }

    pub fn get_weight(&self, from: &SpaceCoordinates, to: &SpaceCoordinates) -> Option<f64> {
        self.edges
            .get(from)
            .and_then(|vec| vec.iter().find(|(t, _)| t == to).map(|(_, w)| *w))
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
