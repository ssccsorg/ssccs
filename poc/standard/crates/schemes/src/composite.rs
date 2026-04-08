//! Composite and Transformed Scheme extensions

use ssccs_core::{Segment, SegmentId, SpaceCoordinates};
use ssccs_primitive::{Axis, LogicalAddress, SchemeId, SchemeImpl, SchemeTrait};
use std::collections::HashMap;
use std::sync::Arc;

// Type alias for complex closure types
type CustomCombinerFn = Arc<dyn Fn(&[&SchemeImpl]) -> SchemeImpl + Send + Sync>;

/// Composite Scheme (composition of multiple Schemes)
#[derive(Clone, Debug)]
pub struct CompositeScheme {
    id: SchemeId,
    components: Vec<SchemeImpl>,
    #[allow(dead_code)]
    composition_rules: CompositionRules,
}

impl CompositeScheme {
    /// Create a new composite scheme from components and composition rules.
    /// The ID is derived by hashing the component IDs and the composition rules.
    pub fn new(components: Vec<SchemeImpl>, composition_rules: CompositionRules) -> Self {
        use blake3;
        let mut hasher = blake3::Hasher::new();
        // Include component IDs
        for component in &components {
            hasher.update(component.id().as_bytes());
        }
        // Include combination method discriminant
        match &composition_rules.combination_method {
            CombinationMethod::Union => {
                hasher.update(b"Union");
            }
            CombinationMethod::Intersection => {
                hasher.update(b"Intersection");
            }
            CombinationMethod::Product => {
                hasher.update(b"Product");
            }
            CombinationMethod::Sum => {
                hasher.update(b"Sum");
            }
            CombinationMethod::Custom(_) => {
                hasher.update(b"Custom");
            }
        }
        // Include alignment and conflict resolution if present
        if let Some(alignment) = &composition_rules.alignment {
            for (a, b) in &alignment.alignment_axes {
                hasher.update(&a.to_be_bytes());
                hasher.update(&b.to_be_bytes());
            }
        }
        match &composition_rules.conflict_resolution {
            ConflictResolution::FirstWins => {
                hasher.update(b"FirstWins");
            }
            ConflictResolution::Priority(order) => {
                hasher.update(b"Priority");
                for idx in order {
                    hasher.update(&idx.to_be_bytes());
                }
            }
            ConflictResolution::Merge => {
                hasher.update(b"Merge");
            }
            ConflictResolution::Fail => {
                hasher.update(b"Fail");
            }
        }
        let id = SchemeId(hasher.finalize().into());
        Self {
            id,
            components,
            composition_rules,
        }
    }
}

/// Composition rules for composite schemes
#[derive(Clone, Debug)]
pub struct CompositionRules {
    pub combination_method: CombinationMethod,
    pub alignment: Option<AlignmentRules>,
    pub conflict_resolution: ConflictResolution,
}

/// Combination method for composite schemes
#[derive(Clone)]
pub enum CombinationMethod {
    Union,        // union
    Intersection, // intersection
    Product,      // Cartesian product
    Sum,          // straight
    Custom(CustomCombinerFn),
}

impl std::fmt::Debug for CombinationMethod {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            CombinationMethod::Union => write!(f, "Union"),
            CombinationMethod::Intersection => write!(f, "Intersection"),
            CombinationMethod::Product => write!(f, "Product"),
            CombinationMethod::Sum => write!(f, "Sum"),
            CombinationMethod::Custom(_) => write!(f, "Custom"),
        }
    }
}

/// Alignment rules for composite schemes
#[derive(Clone, Debug, PartialEq)]
pub struct AlignmentRules {
    pub alignment_axes: Vec<(usize, usize)>, // (comp1_axis_idx, comp2_axis_idx)
    pub tolerance: Option<f64>,
}

/// Conflict resolution strategy
#[derive(Clone, Debug, PartialEq)]
pub enum ConflictResolution {
    FirstWins,            // First Scheme first
    Priority(Vec<usize>), // Priority based
    Merge,                // merge attempt
    Fail,                 // Fail on collision
}

impl SchemeTrait for CompositeScheme {
    fn id(&self) -> &SchemeId {
        &self.id
    }

    fn axes(&self) -> &[Axis] {
        // Composite scheme may have multiple axes; for simplicity return empty slice.
        &[]
    }

    fn dimensionality(&self) -> usize {
        // Return maximum dimensionality among components? For now 0.
        0
    }

    fn contains_segment(&self, segment_id: &SegmentId) -> bool {
        self.components
            .iter()
            .any(|c| c.contains_segment(segment_id))
    }

    fn get_segment(&self, segment_id: &SegmentId) -> Option<&Segment> {
        self.components
            .iter()
            .find_map(|c| c.get_segment(segment_id))
    }

    fn segments(&self) -> Box<dyn Iterator<Item = &Segment> + '_> {
        // Collect segments from all components, deduplicate by SegmentId? For now just chain.
        let iter = self.components.iter().flat_map(|c| c.segments());
        Box::new(iter)
    }

    fn validate_structure(&self, _coords: &SpaceCoordinates) -> Result<(), String> {
        // For composite schemes, validation may be complex; just return OK.
        Ok(())
    }

    fn map_to_logical_address(&self, _coords: &SpaceCoordinates) -> Option<LogicalAddress> {
        // Mapping undefined for composite scheme.
        None
    }

    fn describe(&self) -> String {
        format!("CompositeScheme with {} components", self.components.len())
    }
}

/// Transformed Scheme
#[derive(Clone, Debug)]
pub struct TransformedScheme {
    id: SchemeId,
    base: Box<SchemeImpl>,
    #[allow(dead_code)]
    transformation: Transformation,
}

impl TransformedScheme {
    pub fn new(base: Box<SchemeImpl>, transformation: Transformation) -> Self {
        use blake3;
        let mut hasher = blake3::Hasher::new();
        hasher.update(base.id().as_bytes());
        // Include transformation type discriminant
        match &transformation.transform_type {
            TransformType::Translation(v) => {
                hasher.update(b"Translation");
                for &coord in v {
                    hasher.update(&coord.to_be_bytes());
                }
            }
            TransformType::Rotation(m) => {
                hasher.update(b"Rotation");
                // For simplicity, hash matrix dimensions
                hasher.update(&(m.0.len() as u64).to_be_bytes());
            }
            TransformType::Scaling(v) => {
                hasher.update(b"Scaling");
                for &val in v {
                    hasher.update(&val.to_be_bytes());
                }
            }
            TransformType::Shearing(m) => {
                hasher.update(b"Shearing");
                hasher.update(&(m.0.len() as u64).to_be_bytes());
            }
            TransformType::Projection(m) => {
                hasher.update(b"Projection");
                hasher.update(&(m.0.len() as u64).to_be_bytes());
            }
            TransformType::DimensionalReduction => {
                hasher.update(b"DimensionalReduction");
            }
            TransformType::DimensionalExpansion => {
                hasher.update(b"DimensionalExpansion");
            }
            TransformType::TopologicalTransform => {
                hasher.update(b"TopologicalTransform");
            }
        }
        // Include parameters (sorted for deterministic hash)
        let mut param_keys: Vec<_> = transformation.parameters.keys().collect();
        param_keys.sort();
        for key in param_keys {
            hasher.update(key.as_bytes());
            if let Some(val) = transformation.parameters.get(key) {
                hasher.update(val.as_bytes());
            }
        }
        let id = SchemeId(hasher.finalize().into());
        Self {
            id,
            base,
            transformation,
        }
    }
}

impl SchemeTrait for TransformedScheme {
    fn id(&self) -> &SchemeId {
        &self.id
    }

    fn axes(&self) -> &[Axis] {
        self.base.axes()
    }

    fn dimensionality(&self) -> usize {
        self.base.dimensionality()
    }

    fn contains_segment(&self, segment_id: &SegmentId) -> bool {
        self.base.contains_segment(segment_id)
    }

    fn get_segment(&self, segment_id: &SegmentId) -> Option<&Segment> {
        self.base.get_segment(segment_id)
    }

    fn segments(&self) -> Box<dyn Iterator<Item = &Segment> + '_> {
        self.base.segments()
    }

    fn validate_structure(&self, coords: &SpaceCoordinates) -> Result<(), String> {
        self.base.validate_structure(coords)
    }

    fn map_to_logical_address(&self, coords: &SpaceCoordinates) -> Option<LogicalAddress> {
        self.base.map_to_logical_address(coords)
    }

    fn describe(&self) -> String {
        format!("TransformedScheme: {}", self.base.describe())
    }
}

/// Scheme transformation
#[derive(Clone, Debug)]
pub struct Transformation {
    pub transform_type: TransformType,
    pub parameters: HashMap<String, String>,
}

/// Transform type enumeration
#[derive(Clone, Debug, PartialEq)]
pub enum TransformType {
    Translation(Vec<i64>),   // parallel movement
    Rotation(Matrix<f64>),   // rotation
    Scaling(Vec<f64>),       // scaling
    Shearing(Matrix<f64>),   // shear conversion
    Projection(Matrix<f64>), // projection
    DimensionalReduction,    // dimensionality reduction
    DimensionalExpansion,    // dimension expansion
    TopologicalTransform,    // Topology Transformation
}

/// Simple matrix type for transformations
#[derive(Clone, Debug, PartialEq)]
pub struct Matrix<T>(pub Vec<Vec<T>>);

impl<T> Matrix<T> {
    pub fn new(data: Vec<Vec<T>>) -> Self {
        Matrix(data)
    }
}
