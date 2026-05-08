//! Field synthesis research crate.
//!
//! This crate explores techniques for synthesizing fields from high-level specifications
//! and validates Field composition algebra: the epistemology of inquiry.
//!
//! ## Core Concept
//!
//! The philosophy document establishes that composing Fields is a form of epistemology:
//!
//! - **Union (∪)**: Broadens inquiry — a coordinate is admissible if any constituent Field allows it.
//! - **Intersection (∩)**: Narrows focus — a coordinate is admissible only if all constituent Fields allow it.
//! - **Product (×)**: Independent parallel investigation — constraints apply to disjoint axis partitions.
//!
//! These are not algebraic conveniences. They are the structure of inquiry made directly executable.

use std::fmt::Debug;

pub use ssccs_core::{Constraint, Field, Projector, Segment, SpaceCoordinates};

// ==================== COMPOSITION OPERATION ====================

/// The algebraic operation that composes two Fields.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum CompositionOp {
    /// Union (∪): coordinate is admissible if either Field allows it.
    /// Broadens the inquiry.
    Union,
    /// Intersection (∩): coordinate is admissible only if both Fields allow it.
    /// Narrows the focus.
    Intersection,
    /// Product (×): independent parallel investigation.
    /// Left Field constrains the first k axes, right Field constrains the remaining axes.
    Product,
}

impl CompositionOp {
    /// Returns the identity element for this operation.
    pub fn identity(&self) -> IdentityField {
        match self {
            CompositionOp::Union => IdentityField::Empty, // A ∪ ∅ = A
            CompositionOp::Intersection => IdentityField::Universal, // A ∩ ⊤ = A
            CompositionOp::Product => IdentityField::Unit, // A × () = A
        }
    }

    /// Returns a human-readable symbol.
    pub fn symbol(&self) -> &'static str {
        match self {
            CompositionOp::Union => "∪",
            CompositionOp::Intersection => "∩",
            CompositionOp::Product => "×",
        }
    }
}

/// Special identity fields for algebraic operations.
#[derive(Debug, Clone)]
pub enum IdentityField {
    /// Empty Field: no coordinate is admissible. Identity for Union.
    Empty,
    /// Universal Field: every coordinate is admissible. Identity for Intersection.
    Universal,
    /// Unit Field: zero-dimensional (single point). Identity for Product.
    Unit,
}

impl IdentityField {
    /// Check whether a coordinate is admissible in this identity field.
    pub fn allows(&self, _coords: &SpaceCoordinates) -> bool {
        match self {
            IdentityField::Empty => false,
            IdentityField::Universal => true,
            IdentityField::Unit => {
                // Zero-dimensional space: only the empty coordinate is admissible.
                _coords.raw.is_empty()
            }
        }
    }
}

// ==================== COMPOSED FIELD ====================

/// A Field composed from sub-Fields using an algebraic operation.
///
/// A ComposedField implements the epistemology of inquiry:
/// - Union: "what if I ask broadly across multiple constraint regimes?"
/// - Intersection: "what if I demand satisfaction across multiple criteria?"
/// - Product: "what if I investigate independent dimensions simultaneously?"
#[derive(Debug, Clone)]
pub struct ComposedField {
    /// The left (or first) sub-field.
    left: ComposedExpr,
    /// The right (or second) sub-field.
    right: ComposedExpr,
    /// The composition operation.
    op: CompositionOp,
    /// Cached axis count for product operations.
    left_axes: Option<usize>,
}

/// A recursive expression tree for Field composition.
#[derive(Debug, Clone)]
pub enum ComposedExpr {
    /// A concrete Field instance.
    Field(Field),
    /// An identity field (empty, universal, or unit).
    Identity(IdentityField),
    /// A nested composition.
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
    /// Create a new composed field from two sub-expressions and an operation.
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

    /// Set the axis count for the left operand in a Product composition.
    /// This determines how many axes the left Field constrains.
    pub fn with_left_axes(mut self, axes: usize) -> Self {
        self.left_axes = Some(axes);
        self
    }

    /// Evaluate whether a coordinate is admissible in the composed Field.
    /// Delegates to the appropriate composition rule.
    pub fn allows(&self, coords: &SpaceCoordinates) -> bool {
        match self.op {
            CompositionOp::Union => self.eval_left(coords) || self.eval_right(coords),
            CompositionOp::Intersection => self.eval_left(coords) && self.eval_right(coords),
            CompositionOp::Product => {
                match self.left_axes {
                    Some(axes) => {
                        // Split coordinate space: left gets first `axes` axes, right gets the rest.
                        let left_coords = SpaceCoordinates::new(coords.raw[..axes].to_vec());
                        let right_coords = SpaceCoordinates::new(coords.raw[axes..].to_vec());
                        self.eval_expr(&self.left, &left_coords)
                            && self.eval_expr(&self.right, &right_coords)
                    }
                    None => {
                        // No split: both Fields see the full coordinate space independently.
                        self.eval_left(coords) && self.eval_right(coords)
                    }
                }
            }
        }
    }

    /// Get the composition operation.
    pub fn op(&self) -> CompositionOp {
        self.op
    }

    /// Return a human-readable description of the composition expression.
    pub fn describe(&self) -> String {
        let left_desc = self.describe_expr(&self.left);
        let right_desc = self.describe_expr(&self.right);
        format!("({} {} {})", left_desc, self.op.symbol(), right_desc)
    }

    // ---- internal helpers ----

    fn eval_left(&self, coords: &SpaceCoordinates) -> bool {
        self.eval_expr(&self.left, coords)
    }

    fn eval_right(&self, coords: &SpaceCoordinates) -> bool {
        self.eval_expr(&self.right, coords)
    }

    fn eval_expr(&self, expr: &ComposedExpr, coords: &SpaceCoordinates) -> bool {
        match expr {
            ComposedExpr::Field(f) => f.allows(coords),
            ComposedExpr::Identity(id) => id.allows(coords),
            ComposedExpr::Composed(inner) => inner.allows(coords),
        }
    }

    fn describe_expr(&self, expr: &ComposedExpr) -> String {
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
}

// ==================== FIELD SYNTHESIS FUNCTIONS ====================

/// Construct a Field that represents the **union** of two constraint regimes.
/// A coordinate is admissible if either constituent Field allows it.
///
/// Corresponds to broadening the inquiry.
pub fn union(left: impl Into<ComposedExpr>, right: impl Into<ComposedExpr>) -> ComposedField {
    ComposedField::new(left, right, CompositionOp::Union)
}

/// Construct a Field that represents the **intersection** of two constraint regimes.
/// A coordinate is admissible only if both constituent Fields allow it.
///
/// Corresponds to narrowing the focus.
pub fn intersection(
    left: impl Into<ComposedExpr>,
    right: impl Into<ComposedExpr>,
) -> ComposedField {
    ComposedField::new(left, right, CompositionOp::Intersection)
}

/// Construct a Field that represents the **product** of two constraint regimes.
/// Each Field constrains an independent axis partition.
/// `left_axes` specifies how many axes the left Field governs.
///
/// Corresponds to pursuing independent lines of investigation in parallel.
pub fn product(
    left: impl Into<ComposedExpr>,
    right: impl Into<ComposedExpr>,
    left_axes: usize,
) -> ComposedField {
    ComposedField::new(left, right, CompositionOp::Product).with_left_axes(left_axes)
}
