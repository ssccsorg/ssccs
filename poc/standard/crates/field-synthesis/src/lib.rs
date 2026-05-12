//! Field synthesis research crate.
//!
//! This crate validates Field composition algebra: the epistemology of inquiry.
//!
//! - **Union (∪)**: Broadens inquiry — admissible if any constituent Field allows it.
//! - **Intersection (∩)**: Narrows focus — admissible only if all constituent Fields allow it.
//! - **Product (×)**: Parallel independent investigation — each Field governs a disjoint
//!   axis partition. Requires explicit `left_axes`.
//!
//! These are not algebraic conveniences. They are the structure of inquiry made executable.

use std::collections::HashSet;
use std::fmt::Debug;

pub use ssccs_core::{Constraint, Field, Projector, Segment, SegmentId, SpaceCoordinates};

// ==================== COMPOSITION OPERATION ====================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CompositionOp {
    Union,
    Intersection,
    Product,
}

impl CompositionOp {
    pub fn identity(&self) -> IdentityField {
        match self {
            CompositionOp::Union => IdentityField::Empty,
            CompositionOp::Intersection => IdentityField::Universal,
            CompositionOp::Product => IdentityField::Unit,
        }
    }

    pub fn symbol(&self) -> &'static str {
        match self {
            CompositionOp::Union => "∪",
            CompositionOp::Intersection => "∩",
            CompositionOp::Product => "×",
        }
    }
}

#[derive(Debug, Clone)]
pub enum IdentityField {
    Empty,
    Universal,
    Unit,
}

impl IdentityField {
    pub fn allows(&self, coords: &SpaceCoordinates) -> bool {
        match self {
            IdentityField::Empty => false,
            IdentityField::Universal => true,
            IdentityField::Unit => coords.raw.is_empty(),
        }
    }
}

// ==================== COMPOSED FIELD ====================

#[derive(Debug, Clone)]
pub struct ComposedField {
    left: ComposedExpr,
    right: ComposedExpr,
    op: CompositionOp,
    left_axes: Option<usize>,
}

#[derive(Debug, Clone)]
pub enum ComposedExpr {
    Field(Field),
    Identity(IdentityField),
    Composed(Box<ComposedField>),
}

impl From<Field> for ComposedExpr {
    fn from(f: Field) -> Self {
        ComposedExpr::Field(f)
    }
}
impl From<IdentityField> for ComposedExpr {
    fn from(id: IdentityField) -> Self {
        ComposedExpr::Identity(id)
    }
}
impl From<ComposedField> for ComposedExpr {
    fn from(cf: ComposedField) -> Self {
        ComposedExpr::Composed(Box::new(cf))
    }
}

impl ComposedField {
    pub fn new(
        left: impl Into<ComposedExpr>,
        right: impl Into<ComposedExpr>,
        op: CompositionOp,
    ) -> Self {
        Self {
            left: left.into(),
            right: right.into(),
            op,
            left_axes: None,
        }
    }

    pub fn with_left_axes(mut self, axes: usize) -> Self {
        self.left_axes = Some(axes);
        self
    }
    pub fn op(&self) -> CompositionOp {
        self.op
    }

    // ---- admissibility ----

    pub fn allows(&self, coords: &SpaceCoordinates) -> bool {
        match self.op {
            CompositionOp::Union => eval_expr(&self.left, coords) || eval_expr(&self.right, coords),
            CompositionOp::Intersection => {
                eval_expr(&self.left, coords) && eval_expr(&self.right, coords)
            }
            CompositionOp::Product => {
                let axes = self
                    .left_axes
                    .expect("Product requires axis partition — use product() or with_left_axes()");
                if axes > coords.raw.len() {
                    return false;
                }
                let left_coords = SpaceCoordinates::new(coords.raw[..axes].to_vec());
                let right_pass = if axes >= coords.raw.len() {
                    true // all axes consumed; right field has zero dimensions
                } else {
                    let right_coords = SpaceCoordinates::new(coords.raw[axes..].to_vec());
                    eval_expr(&self.right, &right_coords)
                };
                eval_expr(&self.left, &left_coords) && right_pass
            }
        }
    }

    // ---- transitions ----

    pub fn transition_targets(&self, coords: &SpaceCoordinates) -> Vec<SegmentId> {
        match self.op {
            CompositionOp::Union => {
                let mut merged = transition_expr(&self.left, coords);
                merged.extend(transition_expr(&self.right, coords));
                merged.sort();
                merged.dedup();
                merged
            }
            CompositionOp::Intersection => {
                let left: HashSet<SegmentId> =
                    transition_expr(&self.left, coords).into_iter().collect();
                let right: HashSet<SegmentId> =
                    transition_expr(&self.right, coords).into_iter().collect();
                let mut merged: Vec<SegmentId> = left.intersection(&right).cloned().collect();
                merged.sort();
                merged
            }
            CompositionOp::Product => {
                let axes = self
                    .left_axes
                    .expect("Product requires axis partition — use product() or with_left_axes()");
                if axes > coords.raw.len() {
                    return Vec::new();
                }
                let left_coords = SpaceCoordinates::new(coords.raw[..axes].to_vec());
                let right_coords = SpaceCoordinates::new(coords.raw[axes..].to_vec());
                let left_targets: Vec<SegmentId> = transition_expr(&self.left, &left_coords);
                let right_targets: Vec<SegmentId> = transition_expr(&self.right, &right_coords);
                let mut merged = left_targets;
                merged.extend(right_targets);
                merged.sort();
                merged.dedup();
                merged
            }
        }
    }

    pub fn describe(&self) -> String {
        format!(
            "({} {} {})",
            describe_expr(&self.left),
            self.op.symbol(),
            describe_expr(&self.right)
        )
    }
}

// ---- free evaluation functions ----

fn eval_expr(expr: &ComposedExpr, coords: &SpaceCoordinates) -> bool {
    match expr {
        ComposedExpr::Field(f) => f.allows(coords),
        ComposedExpr::Identity(id) => id.allows(coords),
        ComposedExpr::Composed(inner) => inner.allows(coords),
    }
}

fn transition_expr(expr: &ComposedExpr, coords: &SpaceCoordinates) -> Vec<SegmentId> {
    match expr {
        ComposedExpr::Field(f) => f.transition_targets(coords),
        ComposedExpr::Identity(_) => Vec::new(),
        ComposedExpr::Composed(inner) => inner.transition_targets(coords),
    }
}

fn describe_expr(expr: &ComposedExpr) -> String {
    match expr {
        ComposedExpr::Field(f) => format!("Field({})", f.describe_constraints()),
        ComposedExpr::Identity(id) => match id {
            IdentityField::Empty => "∅".to_string(),
            IdentityField::Universal => "⊤".to_string(),
            IdentityField::Unit => "()".to_string(),
        },
        ComposedExpr::Composed(inner) => inner.describe(),
    }
}

// ==================== FIELD SYNTHESIS FUNCTIONS ====================

pub fn union(left: impl Into<ComposedExpr>, right: impl Into<ComposedExpr>) -> ComposedField {
    ComposedField::new(left, right, CompositionOp::Union)
}

pub fn intersection(
    left: impl Into<ComposedExpr>,
    right: impl Into<ComposedExpr>,
) -> ComposedField {
    ComposedField::new(left, right, CompositionOp::Intersection)
}

pub fn product(
    left: impl Into<ComposedExpr>,
    right: impl Into<ComposedExpr>,
    left_axes: usize,
) -> ComposedField {
    ComposedField::new(left, right, CompositionOp::Product).with_left_axes(left_axes)
}

// ==================== OBSERVATION BRIDGE ====================

/// Observe a Segment through a composed Field.
///
/// The composed Field gates projection: only coordinates that satisfy all composition
/// rules produce a result. This bridges composition (the epistemology of inquiry) with
/// the observation pipeline — making "directly executable" structurally real.
pub fn compose_observe<P: Projector>(
    composed: &ComposedField,
    projector: &P,
    segment: &Segment,
) -> Option<P::Output> {
    if composed.allows(segment.coordinates()) {
        projector.project(&Field::new(), segment)
    } else {
        None
    }
}
