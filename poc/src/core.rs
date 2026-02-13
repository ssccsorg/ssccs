//! SSCCS Proof of Concept – Core Library
//!
//! This crate provides the fundamental building blocks of the SSCCS paradigm:
//! - Immutable `SchemaSegment`
//! - Mutable `Field` (constraints + relational topology)
//! - `Projector` trait for semantic interpretation
//! - Observation functions that combine segment and field
//!
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
/// Derived from the segment's intrinsic properties (coordinates + basic adjacency).
#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct SegmentId([u8; 32]);

impl SegmentId {
    pub fn as_bytes(&self) -> &[u8; 32] {
        &self.0
    }
}

/// An immutable blueprint that defines a location and its intrinsic neighbours.
/// This trait is object‑safe, so it can be used via `dyn SchemeSegment`.
pub trait SchemeSegment: Debug + Send + Sync {
    /// The coordinates of this segment.
    fn coordinates(&self) -> SpaceCoordinates;

    /// Intrinsic, immutable adjacency (e.g. +1/-1 on each axis).
    /// These are part of the segment's definition, not the field.
    fn basic_adjacency(&self) -> Vec<SpaceCoordinates>;

    /// Cryptographic identity derived from the segment's immutable properties.
    /// Default implementation hashes the coordinates and the basic adjacency list.
    fn identity(&self) -> SegmentId {
        let mut hasher = blake3::Hasher::new();
        // Hash coordinates
        for v in self.coordinates().raw.iter() {
            hasher.update(&v.to_le_bytes());
        }
        // Hash basic adjacency (order matters – we sort to ensure determinism)
        let mut adj = self.basic_adjacency();
        adj.sort_by(|a, b| a.raw.cmp(&b.raw));
        for coord in adj {
            for v in coord.raw.iter() {
                hasher.update(&v.to_le_bytes());
            }
        }
        SegmentId(hasher.finalize().into())
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
        self.edges
            .entry(from)
            .or_insert_with(Vec::new)
            .push((to, weight));
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

/// A projector gives semantic meaning to a combination of Field and SchemaSegment.
/// The output is the "collapsed cross‑section" of the constraint space at that point.
pub trait Projector: Debug + Send + Sync {
    type Output: Clone + Debug + PartialEq + Eq + Hash;

    /// Produce a projection, if possible. The projector may use both the field's constraints
    /// and the segment's intrinsic properties.
    fn project(&self, field: &Field, segment: &dyn SchemeSegment) -> Option<Self::Output>;
}
