use std::collections::HashMap;

pub mod core;
pub use core::*;

// ==================== CONSTRAINT IMPLEMENTATIONS ====================

/// Constraint that an axis must lie within a given inclusive range.
#[derive(Debug, Clone)]
pub struct RangeConstraint {
    axis: usize,
    min: i64,
    max: i64,
}

impl RangeConstraint {
    pub fn new(axis: usize, min: i64, max: i64) -> Self {
        Self { axis, min, max }
    }
}

impl Constraint for RangeConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v >= self.min && v <= self.max)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] ∈ [{}, {}]", self.axis, self.min, self.max)
    }
}

/// Constraint that an axis must be even.
#[derive(Debug, Clone)]
pub struct EvenConstraint {
    axis: usize,
}

impl EvenConstraint {
    pub fn new(axis: usize) -> Self {
        Self { axis }
    }
}

impl Constraint for EvenConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v % 2 == 0)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] is even", self.axis)
    }
}

// ==================== NEW CONSTRAINT IMPLEMENTATIONS (from ev) ====================

/// Constraint that two axes must have different values.
#[derive(Debug, Clone)]
pub struct NeqConstraint {
    axis_a: usize,
    axis_b: usize,
}

impl NeqConstraint {
    pub fn new(axis_a: usize, axis_b: usize) -> Self {
        Self { axis_a, axis_b }
    }
}

impl Constraint for NeqConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        match (coords.get_axis(self.axis_a), coords.get_axis(self.axis_b)) {
            (Some(a), Some(b)) => a != b,
            _ => false,
        }
    }

    fn describe(&self) -> String {
        format!("axis[{}] != axis[{}]", self.axis_a, self.axis_b)
    }
}

/// Constraint that an axis value must be less than a threshold.
#[derive(Debug, Clone)]
pub struct LtConstraint {
    axis: usize,
    threshold: i64,
}

impl LtConstraint {
    pub fn new(axis: usize, threshold: i64) -> Self {
        Self { axis, threshold }
    }
}

impl Constraint for LtConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v < self.threshold)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] < {}", self.axis, self.threshold)
    }
}

/// Constraint that an axis value must be greater than a threshold.
#[derive(Debug, Clone)]
pub struct GtConstraint {
    axis: usize,
    threshold: i64,
}

impl GtConstraint {
    pub fn new(axis: usize, threshold: i64) -> Self {
        Self { axis, threshold }
    }
}

impl Constraint for GtConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v > self.threshold)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] > {}", self.axis, self.threshold)
    }
}

/// Constraint that an axis value must be less than or equal to a threshold.
#[derive(Debug, Clone)]
pub struct LeConstraint {
    axis: usize,
    threshold: i64,
}

impl LeConstraint {
    pub fn new(axis: usize, threshold: i64) -> Self {
        Self { axis, threshold }
    }
}

impl Constraint for LeConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v <= self.threshold)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] <= {}", self.axis, self.threshold)
    }
}

/// Constraint that an axis value must be greater than or equal to a threshold.
#[derive(Debug, Clone)]
pub struct GeConstraint {
    axis: usize,
    threshold: i64,
}

impl GeConstraint {
    pub fn new(axis: usize, threshold: i64) -> Self {
        Self { axis, threshold }
    }
}

impl Constraint for GeConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| v >= self.threshold)
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("axis[{}] >= {}", self.axis, self.threshold)
    }
}

/// Constraint that an axis value must be one of a set of allowed values.
#[derive(Debug, Clone)]
pub struct OneOfConstraint {
    axis: usize,
    values: Vec<i64>,
}

impl OneOfConstraint {
    pub fn new(axis: usize, values: Vec<i64>) -> Self {
        Self { axis, values }
    }
}

impl Constraint for OneOfConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(self.axis)
            .map(|v| self.values.contains(&v))
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!(
            "axis[{}] ∈ {{{}}}",
            self.axis,
            self.values
                .iter()
                .map(|v| v.to_string())
                .collect::<Vec<_>>()
                .join(", ")
        )
    }
}

/// Constraint that maps axis_a values to allowed axis_b value sets.
/// If axis_a's value is not in the mapping, the constraint passes (no restriction).
#[derive(Debug, Clone)]
pub struct CrossConstraint {
    axis_a: usize,
    axis_b: usize,
    mapping: HashMap<i64, Vec<i64>>,
}

impl CrossConstraint {
    pub fn new(axis_a: usize, axis_b: usize, mapping: HashMap<i64, Vec<i64>>) -> Self {
        Self {
            axis_a,
            axis_b,
            mapping,
        }
    }
}

impl Constraint for CrossConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        match (coords.get_axis(self.axis_a), coords.get_axis(self.axis_b)) {
            (Some(a), Some(b)) => {
                match self.mapping.get(&a) {
                    Some(allowed) => allowed.contains(&b),
                    // If axis_a value not in mapping, no restriction.
                    None => true,
                }
            }
            _ => false,
        }
    }

    fn describe(&self) -> String {
        let entries: Vec<String> = self
            .mapping
            .iter()
            .map(|(k, v)| {
                format!(
                    "{} → {{{}}}",
                    k,
                    v.iter()
                        .map(|x| x.to_string())
                        .collect::<Vec<_>>()
                        .join(", ")
                )
            })
            .collect();
        format!(
            "axis[{}] × axis[{}]: {}",
            self.axis_a,
            self.axis_b,
            entries.join("; ")
        )
    }
}

// ==================== OBSERVATION FUNCTIONS ====================

/// Observe a single point: project if the coordinate is allowed by the field.
pub fn observe<P: Projector>(field: &Field, segment: &Segment, projector: &P) -> Option<P::Output> {
    if field.allows(segment.coordinates()) {
        projector.project(field, segment)
    } else {
        None
    }
}

/// Compute all possible next SegmentIds from the current segment, taking into account
/// both the projector's interpretation of adjacency and the field's transition matrix,
/// filtered by field constraints.
pub fn possible_next_coordinates<P: Projector>(
    field: &Field,
    segment: &Segment,
    projector: &P,
) -> Vec<SegmentId> {
    let current = segment.coordinates();
    let projector_candidates = projector.possible_next_coordinates(current);
    let mut candidates: Vec<SegmentId> = projector_candidates
        .into_iter()
        .filter(|c| field.allows(c))
        .map(|c| segment_id_from_coords(&c))
        .collect();
    candidates.extend(field.transition_targets(current));
    candidates.sort();
    candidates.dedup();
    candidates
}

// ==================== TESTS ====================

#[cfg(test)]
mod tests {
    use super::*;

    // These tests cover constraint types defined in this crate.
    // observe_all() tests live in ssccs-primitive (which has SchemeTrait).

    // ── NeqConstraint ──

    #[test]
    fn neq_allows_different_values() {
        let c = NeqConstraint::new(0, 1);
        let coords = Coordinates::new(vec![3, 5]);
        assert!(c.allows(&coords));
    }

    #[test]
    fn neq_rejects_equal_values() {
        let c = NeqConstraint::new(0, 1);
        let coords = Coordinates::new(vec![7, 7]);
        assert!(!c.allows(&coords));
    }

    #[test]
    fn neq_missing_axis_returns_false() {
        let c = NeqConstraint::new(0, 3);
        let coords = Coordinates::new(vec![1, 2]);
        assert!(!c.allows(&coords));
    }

    // ── LtConstraint ──

    #[test]
    fn lt_allows_below_threshold() {
        let c = LtConstraint::new(0, 10);
        let coords = Coordinates::new(vec![5]);
        assert!(c.allows(&coords));
    }

    #[test]
    fn lt_rejects_at_threshold() {
        let c = LtConstraint::new(0, 10);
        let coords = Coordinates::new(vec![10]);
        assert!(!c.allows(&coords));
    }

    #[test]
    fn lt_rejects_above_threshold() {
        let c = LtConstraint::new(0, 10);
        let coords = Coordinates::new(vec![15]);
        assert!(!c.allows(&coords));
    }

    // ── GtConstraint ──

    #[test]
    fn gt_allows_above_threshold() {
        let c = GtConstraint::new(0, 10);
        let coords = Coordinates::new(vec![15]);
        assert!(c.allows(&coords));
    }

    #[test]
    fn gt_rejects_at_threshold() {
        let c = GtConstraint::new(0, 10);
        let coords = Coordinates::new(vec![10]);
        assert!(!c.allows(&coords));
    }

    #[test]
    fn gt_rejects_below_threshold() {
        let c = GtConstraint::new(0, 10);
        let coords = Coordinates::new(vec![5]);
        assert!(!c.allows(&coords));
    }

    // ── LeConstraint ──

    #[test]
    fn le_allows_below_or_equal() {
        let c = LeConstraint::new(0, 10);
        assert!(c.allows(&Coordinates::new(vec![5])));
        assert!(c.allows(&Coordinates::new(vec![10])));
    }

    #[test]
    fn le_rejects_above() {
        let c = LeConstraint::new(0, 10);
        assert!(!c.allows(&Coordinates::new(vec![15])));
    }

    // ── GeConstraint ──

    #[test]
    fn ge_allows_above_or_equal() {
        let c = GeConstraint::new(0, 10);
        assert!(c.allows(&Coordinates::new(vec![15])));
        assert!(c.allows(&Coordinates::new(vec![10])));
    }

    #[test]
    fn ge_rejects_below() {
        let c = GeConstraint::new(0, 10);
        assert!(!c.allows(&Coordinates::new(vec![5])));
    }

    // ── OneOfConstraint ──

    #[test]
    fn oneof_allows_member() {
        let c = OneOfConstraint::new(0, vec![2, 4, 6, 8]);
        assert!(c.allows(&Coordinates::new(vec![4])));
    }

    #[test]
    fn oneof_rejects_non_member() {
        let c = OneOfConstraint::new(0, vec![2, 4, 6, 8]);
        assert!(!c.allows(&Coordinates::new(vec![5])));
    }

    #[test]
    fn oneof_empty_set_rejects_all() {
        let c = OneOfConstraint::new(0, vec![]);
        assert!(!c.allows(&Coordinates::new(vec![0])));
    }

    // ── CrossConstraint ──

    #[test]
    fn cross_allows_mapped_pair() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1, 2]);
        mapping.insert(1, vec![3, 4]);
        let c = CrossConstraint::new(0, 1, mapping);
        assert!(c.allows(&Coordinates::new(vec![0, 1])));
        assert!(c.allows(&Coordinates::new(vec![1, 3])));
    }

    #[test]
    fn cross_rejects_unmapped_pair() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1]);
        let c = CrossConstraint::new(0, 1, mapping);
        assert!(!c.allows(&Coordinates::new(vec![0, 5])));
    }

    #[test]
    fn cross_passes_when_axis_a_not_in_mapping() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1]);
        let c = CrossConstraint::new(0, 1, mapping);
        // axis_a=5 not in mapping → no restriction
        assert!(c.allows(&Coordinates::new(vec![5, 99])));
    }

    // ── describe() ──

    #[test]
    fn neq_describe() {
        let c = NeqConstraint::new(0, 1);
        assert_eq!(c.describe(), "axis[0] != axis[1]");
    }

    #[test]
    fn lt_describe() {
        let c = LtConstraint::new(2, 100);
        assert_eq!(c.describe(), "axis[2] < 100");
    }

    #[test]
    fn oneof_describe() {
        let c = OneOfConstraint::new(0, vec![1, 3, 5]);
        assert_eq!(c.describe(), "axis[0] ∈ {1, 3, 5}");
    }

    #[test]
    fn cross_describe() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![10, 20]);
        let c = CrossConstraint::new(0, 1, mapping);
        let desc = c.describe();
        assert!(desc.contains("axis[0] × axis[1]"));
        assert!(desc.contains("0 → {10, 20}"));
    }

    // ── Integration: ConstraintSet with multiple new constraints ──

    #[test]
    fn constraint_set_combines_new_types() {
        let mut set = ConstraintSet::new();
        set.add(LtConstraint::new(0, 10));
        set.add(GtConstraint::new(0, 0));
        // coord=5: 0 < 5 < 10 → passes
        assert!(set.allows(&Coordinates::new(vec![5])));
        // coord=0: 0 < 0? no → fails
        assert!(!set.allows(&Coordinates::new(vec![0])));
        // coord=10: 10 < 10? no → fails
        assert!(!set.allows(&Coordinates::new(vec![10])));
    }

    #[test]
    fn constraint_set_with_neq_and_range() {
        let mut set = ConstraintSet::new();
        set.add(RangeConstraint::new(0, 1, 5));
        set.add(RangeConstraint::new(1, 1, 5));
        set.add(NeqConstraint::new(0, 1));
        // (2, 3): both in range, different → passes
        assert!(set.allows(&Coordinates::new(vec![2, 3])));
        // (2, 2): both in range, equal → fails
        assert!(!set.allows(&Coordinates::new(vec![2, 2])));
        // (6, 3): first out of range → fails
        assert!(!set.allows(&Coordinates::new(vec![6, 3])));
    }

    // ── Edge cases for existing constraints ──

    #[test]
    fn range_constraint_single_value_range() {
        let c = RangeConstraint::new(0, 5, 5);
        assert!(c.allows(&Coordinates::new(vec![5])));
        assert!(!c.allows(&Coordinates::new(vec![4])));
        assert!(!c.allows(&Coordinates::new(vec![6])));
    }

    #[test]
    fn range_constraint_negative_range() {
        let c = RangeConstraint::new(0, -10, -1);
        assert!(c.allows(&Coordinates::new(vec![-5])));
        assert!(c.allows(&Coordinates::new(vec![-10])));
        assert!(!c.allows(&Coordinates::new(vec![0])));
        assert!(!c.allows(&Coordinates::new(vec![-11])));
    }

    #[test]
    fn even_constraint_negative_values() {
        let c = EvenConstraint::new(0);
        assert!(c.allows(&Coordinates::new(vec![-4])));
        assert!(c.allows(&Coordinates::new(vec![0])));
        assert!(c.allows(&Coordinates::new(vec![2])));
        assert!(!c.allows(&Coordinates::new(vec![-3])));
        assert!(!c.allows(&Coordinates::new(vec![1])));
    }

    // ── Edge cases for new constraints ──

    #[test]
    fn neq_same_axis_rejects_all() {
        // Asking axis[0] != axis[0] is always false
        let c = NeqConstraint::new(0, 0);
        assert!(!c.allows(&Coordinates::new(vec![5, 3])));
        assert!(!c.allows(&Coordinates::new(vec![0, 0])));
    }

    #[test]
    fn lt_zero_threshold() {
        let c = LtConstraint::new(0, 0);
        assert!(c.allows(&Coordinates::new(vec![-1])));
        assert!(!c.allows(&Coordinates::new(vec![0])));
        assert!(!c.allows(&Coordinates::new(vec![1])));
    }

    #[test]
    fn lt_negative_threshold() {
        let c = LtConstraint::new(0, -5);
        assert!(c.allows(&Coordinates::new(vec![-10])));
        assert!(!c.allows(&Coordinates::new(vec![-5])));
        assert!(!c.allows(&Coordinates::new(vec![0])));
    }

    #[test]
    fn gt_large_threshold() {
        let c = GtConstraint::new(0, i64::MAX - 1);
        assert!(c.allows(&Coordinates::new(vec![i64::MAX])));
        assert!(!c.allows(&Coordinates::new(vec![i64::MAX - 1])));
        assert!(!c.allows(&Coordinates::new(vec![0])));
    }

    #[test]
    fn oneof_single_value() {
        let c = OneOfConstraint::new(0, vec![42]);
        assert!(c.allows(&Coordinates::new(vec![42])));
        assert!(!c.allows(&Coordinates::new(vec![41])));
        assert!(!c.allows(&Coordinates::new(vec![43])));
    }

    #[test]
    fn oneof_large_set() {
        let values: Vec<i64> = (0..100).step_by(2).collect();
        let c = OneOfConstraint::new(0, values);
        assert!(c.allows(&Coordinates::new(vec![50])));
        assert!(c.allows(&Coordinates::new(vec![0])));
        assert!(!c.allows(&Coordinates::new(vec![99])));
        assert!(!c.allows(&Coordinates::new(vec![-2])));
    }

    #[test]
    fn cross_multiple_mappings_with_empty_values() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![]); // opcode 0 allows NO funct3 values
        mapping.insert(1, vec![0, 1, 2]);
        let c = CrossConstraint::new(0, 1, mapping);
        // axis_a=0 has empty allowed list → any axis_b value fails
        assert!(!c.allows(&Coordinates::new(vec![0, 0])));
        assert!(!c.allows(&Coordinates::new(vec![0, 5])));
        // axis_a=1 has [0,1,2] → 0 passes, 5 fails
        assert!(c.allows(&Coordinates::new(vec![1, 0])));
        assert!(!c.allows(&Coordinates::new(vec![1, 5])));
        // axis_a=2 not in mapping → no restriction (passes)
        assert!(c.allows(&Coordinates::new(vec![2, 99])));
    }

    #[test]
    fn cross_missing_axis_b_returns_false() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![10]);
        let c = CrossConstraint::new(0, 3, mapping);
        // only 1 axis, axis_b=3 doesn't exist
        assert!(!c.allows(&Coordinates::new(vec![0])));
    }

    #[test]
    fn ge_negative_threshold() {
        let c = GeConstraint::new(0, -5);
        assert!(c.allows(&Coordinates::new(vec![-5])));
        assert!(c.allows(&Coordinates::new(vec![0])));
        assert!(c.allows(&Coordinates::new(vec![100])));
        assert!(!c.allows(&Coordinates::new(vec![-10])));
        assert!(!c.allows(&Coordinates::new(vec![-6])));
    }

    #[test]
    fn le_negative_threshold() {
        let c = LeConstraint::new(0, -5);
        assert!(c.allows(&Coordinates::new(vec![-10])));
        assert!(c.allows(&Coordinates::new(vec![-5])));
        assert!(!c.allows(&Coordinates::new(vec![0])));
        assert!(!c.allows(&Coordinates::new(vec![-4])));
    }

    #[test]
    fn oneof_duplicate_values_in_set() {
        let c = OneOfConstraint::new(0, vec![1, 1, 2, 2, 3]);
        assert!(c.allows(&Coordinates::new(vec![1])));
        assert!(c.allows(&Coordinates::new(vec![2])));
        assert!(!c.allows(&Coordinates::new(vec![4])));
    }

    #[test]
    fn cross_self_mapping() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1]);
        // self-mapping: axis_a == axis_b, meaning axis[0] value must be in {0,1}
        let c = CrossConstraint::new(0, 0, mapping);
        assert!(c.allows(&Coordinates::new(vec![0])));
        assert!(c.allows(&Coordinates::new(vec![1])));
        // axis_a=2 not in mapping → no restriction
        assert!(c.allows(&Coordinates::new(vec![2])));
    }

    // ── describe() edge cases ──

    #[test]
    fn gt_describe() {
        let c = GtConstraint::new(0, 0);
        assert_eq!(c.describe(), "axis[0] > 0");
    }

    #[test]
    fn le_describe() {
        let c = LeConstraint::new(1, 255);
        assert_eq!(c.describe(), "axis[1] <= 255");
    }

    #[test]
    fn ge_describe() {
        let c = GeConstraint::new(2, -128);
        assert_eq!(c.describe(), "axis[2] >= -128");
    }

    #[test]
    fn cross_describe_empty_mapping() {
        let c = CrossConstraint::new(0, 1, HashMap::new());
        let desc = c.describe();
        assert!(desc.contains("axis[0] × axis[1]"));
    }

    #[test]
    fn range_describe() {
        let c = RangeConstraint::new(0, -128, 127);
        assert_eq!(c.describe(), "axis[0] ∈ [-128, 127]");
    }

    #[test]
    fn even_describe() {
        let c = EvenConstraint::new(3);
        assert_eq!(c.describe(), "axis[3] is even");
    }

    // ── ConstraintSet integration edge cases ──

    #[test]
    fn constraint_set_empty_allows_all() {
        let set = ConstraintSet::new();
        assert!(set.allows(&Coordinates::new(vec![0])));
        assert!(set.allows(&Coordinates::new(vec![i64::MAX])));
        assert!(set.allows(&Coordinates::new(vec![i64::MIN])));
    }

    #[test]
    fn constraint_set_describe_empty() {
        let set = ConstraintSet::new();
        assert_eq!(set.describe(), "no constraints");
    }

    #[test]
    fn constraint_set_describe_multiple() {
        let mut set = ConstraintSet::new();
        set.add(RangeConstraint::new(0, 0, 10));
        set.add(EvenConstraint::new(0));
        let desc = set.describe();
        assert!(desc.contains("axis[0] ∈ [0, 10]"));
        assert!(desc.contains("axis[0] is even"));
    }

    #[test]
    fn constraint_set_all_of_combinators() {
        // coord must satisfy ALL of: lt(10), gt(0), even, oneof({2,4,6,8})
        let mut set = ConstraintSet::new();
        set.add(LtConstraint::new(0, 10));
        set.add(GtConstraint::new(0, 0));
        set.add(EvenConstraint::new(0));
        set.add(OneOfConstraint::new(0, vec![2, 4, 6, 8]));
        assert!(set.allows(&Coordinates::new(vec![2])));
        assert!(set.allows(&Coordinates::new(vec![4])));
        assert!(set.allows(&Coordinates::new(vec![6])));
        assert!(set.allows(&Coordinates::new(vec![8])));
        assert!(!set.allows(&Coordinates::new(vec![1]))); // not even
        assert!(!set.allows(&Coordinates::new(vec![3]))); // not in oneof
        assert!(!set.allows(&Coordinates::new(vec![10]))); // not lt(10)
        assert!(!set.allows(&Coordinates::new(vec![0]))); // not gt(0)
    }

    #[test]
    fn constraint_set_neq_and_oneof() {
        let mut set = ConstraintSet::new();
        set.add(NeqConstraint::new(0, 1));
        set.add(OneOfConstraint::new(0, vec![1, 2, 3]));
        set.add(OneOfConstraint::new(1, vec![1, 2, 3]));
        // (1, 2): both in oneof, different → passes
        assert!(set.allows(&Coordinates::new(vec![1, 2])));
        // (2, 2): both in oneof, equal → fails neq
        assert!(!set.allows(&Coordinates::new(vec![2, 2])));
        // (1, 5): axis[1]=5 not in oneof → fails
        assert!(!set.allows(&Coordinates::new(vec![1, 5])));
    }

    #[test]
    fn constraint_set_cross_with_range() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1]); // opcode 0 → funct3 in {0,1}
        mapping.insert(1, vec![2, 3]); // opcode 1 → funct3 in {2,3}
        let mut set = ConstraintSet::new();
        set.add(CrossConstraint::new(0, 1, mapping));
        set.add(RangeConstraint::new(0, 0, 1)); // opcode in {0,1}
        // (0, 0): opcode 0 in range, funct3 0 in cross → passes
        assert!(set.allows(&Coordinates::new(vec![0, 0])));
        // (0, 2): opcode 0 in range, funct3 2 NOT in cross {0,1} → fails
        assert!(!set.allows(&Coordinates::new(vec![0, 2])));
        // (2, 0): opcode 2 out of range [0,1] → fails range before cross
        assert!(!set.allows(&Coordinates::new(vec![2, 0])));
    }

    // ── Field integration with new constraints ──

    #[test]
    fn field_with_oneof_and_neq() {
        let mut field = Field::new();
        field.add_constraint(OneOfConstraint::new(0, vec![10, 20, 30]));
        field.add_constraint(NeqConstraint::new(0, 1));
        field.add_constraint(RangeConstraint::new(1, 1, 100));
        assert!(field.allows(&Coordinates::new(vec![10, 5])));
        assert!(field.allows(&Coordinates::new(vec![30, 99])));
        assert!(!field.allows(&Coordinates::new(vec![10, 10]))); // neq fails
        assert!(!field.allows(&Coordinates::new(vec![15, 5]))); // oneof fails
        assert!(!field.allows(&Coordinates::new(vec![10, 0]))); // range fails
    }

    #[test]
    fn field_describe_with_new_constraints() {
        let mut field = Field::new();
        field.add_constraint(GtConstraint::new(0, 0));
        field.add_constraint(LtConstraint::new(0, 100));
        let desc = field.describe_constraints();
        assert!(desc.contains("axis[0] > 0"));
        assert!(desc.contains("axis[0] < 100"));
    }

    #[test]
    fn field_with_cross_constraint() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1]);
        mapping.insert(1, vec![2]);
        let mut field = Field::new();
        field.add_constraint(CrossConstraint::new(0, 1, mapping));
        assert!(field.allows(&Coordinates::new(vec![0, 0])));
        assert!(field.allows(&Coordinates::new(vec![1, 2])));
        assert!(!field.allows(&Coordinates::new(vec![0, 5])));
        // axis_a=99 not in mapping → no restriction
        assert!(field.allows(&Coordinates::new(vec![99, 100])));
    }

    // ── Local projectors for observe() tests ──

    /// Returns a fixed axis value.
    #[derive(Debug)]
    struct TestAxisProjector(usize);

    impl Projector for TestAxisProjector {
        type Output = i64;

        fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
            segment.coordinates().get_axis(self.0)
        }
    }

    /// Adds/subtracts 1 to first axis.
    #[derive(Debug)]
    struct TestAdjacencyProjector;

    impl Projector for TestAdjacencyProjector {
        type Output = i64;

        fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
            segment.coordinates().get_axis(0)
        }

        fn possible_next_coordinates(&self, coords: &Coordinates) -> Vec<Coordinates> {
            let v = coords.get_axis(0).unwrap_or(0);
            vec![
                Coordinates::new(vec![v + 1]),
                Coordinates::new(vec![v - 1]),
                Coordinates::new(vec![v * 2]),
                Coordinates::new(vec![v / 2]),
            ]
        }
    }

    #[test]
    fn observe_with_cross_constraint() {
        let mut mapping = HashMap::new();
        mapping.insert(0, vec![0, 1]);
        let mut field = Field::new();
        field.add_constraint(CrossConstraint::new(0, 1, mapping));
        let projector = TestAxisProjector(1);
        let seg = Segment::from_values(vec![0, 42]);
        let result = crate::observe(&field, &seg, &projector);
        assert!(result.is_none()); // 42 not in cross mapping for axis_a=0
    }

    #[test]
    fn observe_with_oneof_rejects() {
        let mut field = Field::new();
        field.add_constraint(OneOfConstraint::new(0, vec![1, 2, 3]));
        let projector = TestAxisProjector(0);
        let seg = Segment::from_value(5);
        let result = crate::observe(&field, &seg, &projector);
        assert!(result.is_none());
    }

    #[test]
    fn possible_next_coordinates_with_new_constraints() {
        let mut field = Field::new();
        field.add_constraint(OneOfConstraint::new(0, vec![1, 2, 3]));
        let projector = TestAdjacencyProjector;
        let seg = Segment::from_value(2);
        let next = crate::possible_next_coordinates(&field, &seg, &projector);
        // TestAdjacencyProjector's next: +1, -1, *2, /2 → filtered by oneof {1,2,3}
        // 2+1=3 ∈ {1,2,3} → included
        // 2-1=1 ∈ {1,2,3} → included
        // 2*2=4 ∉ {1,2,3} → excluded
        // 2/2=1 ∈ {1,2,3} → included (duplicate of 2-1)
        // We verify that the count is filtered correctly (could be 2 or 3)
        assert!(
            next.len() >= 2,
            "should have at least 2 next segments, got {}",
            next.len()
        );
        assert!(
            next.len() <= 3,
            "should have at most 3 next segments, got {}",
            next.len()
        );
    }
}
