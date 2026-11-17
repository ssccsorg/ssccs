//! A constraint as data: one bound kind applied to one coordinate.
//!
//! The description has more than one lowering. The reference assembly emits a branchless gate per spec, and the
//! SystemVerilog emitter instantiates the unit the spec names, so a spec has one meaning and several forms rather
//! than one meaning per emitter.

/// The constraint kinds a substrate carries.
///
/// `Even` takes no bound and the other three take one, with a range taking two. A constraint outside this list has
/// no unit, which makes the list the substrate's vocabulary rather than the whole constraint language.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstraintSpec {
    /// Coordinate value is even.
    Even,
    /// Coordinate value within inclusive bounds.
    Range { min: i64, max: i64 },
    /// Coordinate value equals a constant.
    Eq { value: i64 },
    /// Coordinate value is strictly greater than a constant.
    Gt { value: i64 },
}

/// Host-side semantics of a spec. Every lowering is checked against this function.
pub fn eval_constraint(spec: &ConstraintSpec, value: i64) -> bool {
    match spec {
        ConstraintSpec::Even => value % 2 == 0,
        ConstraintSpec::Range { min, max } => *min <= value && value <= *max,
        ConstraintSpec::Eq { value: target } => value == *target,
        ConstraintSpec::Gt { value: threshold } => value > *threshold,
    }
}
