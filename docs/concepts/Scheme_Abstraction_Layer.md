# Scheme Abstraction Layer: Dimensional Axes, Structural Relations, and Memory Layout

The Scheme abstraction layer in SSCCS defines the structural relationships between Segments without committing to a specific physical memory implementation. This document describes the new Scheme abstraction introduced in the SSCCS proof‑of‑concept, which replaces the earlier `scheme.rs` with a more expressive, flexible, and mathematically grounded architecture.

## 1. Introduction

In SSCCS, a **Scheme** is an immutable blueprint that captures:
- Dimensional axes (coordinate system)
- Structural relations (adjacency, hierarchy, dependency, equivalence, custom predicates)
- Memory‑layout mapping (logical address space)
- Observation rules (resolution strategies, triggers, priorities, context)
- Cryptographic identity (derived from the entire structure)

The new abstraction separates **structural definition** from **physical instantiation**, allowing the same Scheme to be projected onto different hardware topologies, memory layouts, and observation mechanisms.

### 1.1 Why a New Abstraction?

The previous Scheme implementation (`Grid2DScheme`, `IntegerLineScheme`) was tightly coupled to specific dimensional types and a fixed memory‑mapping model. The new design introduces:

- **Axis‑type polymorphism**: discrete, continuous, cyclic, categorical, relational, and unit‑bearing axes.
- **First‑class structural relations**: adjacency, hierarchy, dependency, equivalence, and custom predicates.
- **Memory‑layout abstraction**: linear, row‑major, column‑major, and space‑filling‑curve layouts decoupled from the physical address space.
- **Composite and transformed schemes**: ability to combine multiple schemes or apply geometric/ topologic transformations.
- **Cryptographic identity**: a `SchemeId` derived from a Blake3 hash of the entire structural description, ensuring that any two identical structures share the same identifier.

## 2. Key Architectural Changes

| Old Concept (`scheme.rs`) | New Concept (`abstract_scheme.rs` + `mod.rs`) |
|---------------------------|----------------------------------------------|
| `DimensionType` (Discrete, Continuous) | `AxisType` (Discrete, Continuous, Cyclic, Categorical, Relational, WithUnit) |
| `AdjacencyRelation` (simple enum) | `StructuralRelation` (adjacency, hierarchy, dependency, equivalence, custom) |
| `MemoryLayout` (hard‑coded row‑major) | `MemoryLayout` (layout‑type + mapping closure + metadata) |
| `Grid2DScheme`, `IntegerLineScheme` | `Grid2DTemplate`, `IntegerLineTemplate`, `GraphTemplate` |
| No composite/transformed schemes | `CompositeScheme`, `TransformedScheme` |
| Direct `Segment` storage | `Segment` references stored in a `RelationGraph` |
| No cryptographic identity | `SchemeId` ([u8; 32] Blake3 hash) |

## 3. Core Types and Their Relationships

### 3.1 SchemeId
```rust
pub struct SchemeId(pub [u8; 32]);
```
A 32‑byte cryptographic identifier derived from hashing the entire structural description (axes, segments, relations, constraints, layout, observation rules). Two Schemes with identical content produce the same `SchemeId`.

### 3.2 Axis
```rust
pub struct Axis {
    pub name: String,
    pub axis_type: AxisType,
    pub metadata: HashMap<String, String>,
}
```
An axis defines one dimension of the Scheme’s coordinate space. The `AxisType` can be:
- **Discrete**: integer‑valued (e.g., pixel indices)
- **Continuous**: real‑valued (physical resolution deferred)
- **Cyclic(Option<i64>)**: periodic (e.g., angles modulo 360°)
- **Categorical**: unordered discrete categories
- **Relational(String)**: references another axis by name
- **WithUnit(String)**: physical units (e.g., "meters", "seconds")

### 3.3 StructuralRelation
```rust
pub enum StructuralRelation {
    Adjacency { relation_type: AdjacencyType, weight: Option<f64>, metadata: HashMap<String, String> },
    Hierarchy { parent: SegmentId, depth: i64, relation_type: HierarchyType },
    Dependency { dependent: SegmentId, dependency_type: DependencyType, strength: f64 },
    Equivalence { equivalence_class: u64, symmetry: SymmetryType },
    Custom { name: String, predicate: Arc<dyn Fn(&Segment, &Segment) -> bool + Send + Sync> },
}
```
Structural relations define how Segments are connected or constrained relative to each other. They are stored in a `RelationGraph` and can be filtered when querying for neighbors.

### 3.4 MemoryLayout
```rust
pub struct MemoryLayout {
    pub layout_type: LayoutType,
    pub mapping: Arc<dyn Fn(&SpaceCoordinates) -> Option<LogicalAddress> + Send + Sync>,
    pub metadata: HashMap<String, String>,
}
```
A memory layout defines how a coordinate tuple maps to a logical address. The `LayoutType` describes the high‑level organization (Linear, RowMajor, ColumnMajor, SpaceFillingCurve), while the `mapping` closure implements the precise transformation. Logical addresses are independent of physical memory and can be used by a projector to locate data.

### 3.5 LogicalAddress
```rust
pub struct LogicalAddress {
    pub address: Vec<u8>,
    pub metadata: HashMap<String, String>,
}
```
A variable‑length byte array representing an address in the Scheme’s logical address space. It may include dimensional coordinates, offsets, or any other scheme‑specific encoding.

### 3.6 Scheme
```rust
pub struct Scheme {
    pub id: SchemeId,
    pub axes: Vec<Axis>,
    pub segments: Vec<Segment>,
    pub relation_graph: RelationGraph,
    pub structural_constraints: Vec<StructuralConstraint>,
    pub memory_layout: MemoryLayout,
    pub observation_rules: ObservationRules,
    pub metadata: HashMap<String, String>,
}
```
The immutable blueprint. Once built via a `SchemeBuilder`, it cannot be modified. All structural queries (`structural_neighbors`, `validate_structure`, `map_to_logical_address`) are performed on this object.

### 3.7 RelationGraph
```rust
pub struct RelationGraph {
    nodes: HashMap<SegmentId, Segment>,
    edges: HashMap<(SegmentId, SegmentId), Vec<StructuralRelation>>,
}
```
A directed multigraph that stores all Segments and the relations between them. It supports adding relations, retrieving relations between two Segments, and iterating over neighbors.

### 3.8 SchemeBuilder
```rust
pub struct SchemeBuilder { ... }
```
A builder pattern for constructing a Scheme step‑by‑step. Methods:
- `add_axis`, `add_segment`, `add_segments`, `add_relation`, `add_structural_constraint`
- `set_memory_layout`, `set_observation_rules`, `add_metadata`
- `build()` → `Scheme`

The builder computes the cryptographic hash of the entire structure as each component is added, guaranteeing that the final `SchemeId` is deterministic.

### 3.9 ObservationRules
```rust
pub struct ObservationRules {
    pub resolution_strategy: ResolutionStrategy,
    pub triggers: Vec<ObservationTrigger>,
    pub priority: ObservationPriority,
    pub context: ObservationContext,
}
```
Rules that govern how an Observation is performed on a Field projected through this Scheme. Includes resolution strategy (e.g., `FirstValid`, `WeightedAverage`, `ConstraintSatisfaction`), triggers (`Periodic`, `OnChange`, `OnRequest`), priority, and contextual metadata.

## 4. Templates – Common Scheme Patterns

To simplify creation of frequently used Schemes, the abstraction provides three templates.

### 4.1 Grid2DTemplate
```rust
let template = Grid2DTemplate::new(width, height, GridTopology::FourConnected);
let scheme = template.build();
```
Produces a two‑dimensional grid with a chosen topology (FourConnected, EightConnected, Hexagonal, Triangular). Automatically generates Segments for each grid cell, sets up adjacency relations, and configures a row‑major memory layout.

### 4.2 IntegerLineTemplate
```rust
let template = IntegerLineTemplate::new(start, end, step);
let scheme = template.build();
```
Creates a one‑dimensional discrete line of Segments. Adjacency follows linear ordering, and the memory layout is linear.

### 4.3 GraphTemplate
```rust
let template = GraphTemplate::new();
template.add_node(coords1, segment1);
template.add_edge(segment1_id, segment2_id, relation);
let scheme = template.build();
```
Builds an arbitrary graph of Segments with custom relations. No predefined layout; the memory mapping is left as linear unless overridden.

## 5. Composite and Transformed Schemes

### 5.1 CompositeScheme
```rust
let composite = CompositeScheme::new(
    vec![SchemeImpl::Basic(scheme1), SchemeImpl::Basic(scheme2)],
    CompositionRules {
        combination_method: CombinationMethod::Union,
        alignment_rules: AlignmentRules::default(),
        conflict_resolution: ConflictResolution::Priority(vec![0]),
    }
);
```
A `CompositeScheme` combines multiple `SchemeImpl` components (Basic, Composite, or Transformed) using a set of composition rules. The resulting Scheme’s `SchemeId` is derived from the hash of the component IDs and the composition rules.

Supported combination methods:
- `Union`: logical OR (segment belongs to the composite if it belongs to any component)
- `Intersection`: logical AND (segment must belong to all components)
- `Product`: Cartesian product of component coordinate spaces
- `Sum`: disjoint union (separate coordinate spaces)
- `Custom`: user‑defined combination logic

### 5.2 TransformedScheme
```rust
let transformed = TransformedScheme::new(
    Box::new(SchemeImpl::Basic(base_scheme)),
    Transformation {
        transform_type: TransformType::Translation { dx: 10.0, dy: 0.0 },
        parameters: HashMap::new(),
    }
);
```
Applies a geometric or topological transformation to a base Scheme. Transformations include:
- **Translation**, **Rotation**, **Scaling**, **Shearing**
- **Projection** (dimensional reduction)
- **DimensionalExpansion** (adding a dummy axis)
- **TopologicalTransform** (arbitrary coordinate mapping)

The transformed Scheme’s ID is derived from the base Scheme’s ID and a hash of the transformation parameters.

## 6. SchemeTrait – A Common Interface

All Scheme variants (Basic, Composite, Transformed) implement the `SchemeTrait`:

```rust
pub trait SchemeTrait: std::fmt::Debug + Send + Sync {
    fn id(&self) -> &SchemeId;
    fn axes(&self) -> &[Axis];
    fn dimensionality(&self) -> usize;
    fn contains_segment(&self, segment_id: &SegmentId) -> bool;
    fn get_segment(&self, segment_id: &SegmentId) -> Option<&Segment>;
    fn segments(&self) -> Box<dyn Iterator<Item = &Segment> + '_>;
    fn validate_structure(&self, coords: &SpaceCoordinates) -> Result<(), String>;
    fn map_to_logical_address(&self, coords: &SpaceCoordinates) -> Option<LogicalAddress>;
    fn describe(&self) -> String;
}
```

This trait allows uniform handling of any Scheme variant through the `SchemeImpl` enum.

## 7. Migration Guide

### 7.1 Updating Existing Code

1. **Replace `Grid2DScheme::new(...)`** with `Grid2DTemplate::new(...).build()`.
2. **Replace `IntegerLineScheme::new(...)`** with `IntegerLineTemplate::new(...).build()`.
3. **Change method names**:
   - `map_to_memory` → `map_to_logical_address`
   - `structural_constraints_satisfied` → `validate_structure`
4. **Update adjacency queries**: The old `adjacent_segments` is now accessed via `structural_neighbors` with an optional relation filter.
5. **Handle `DimensionType` → `AxisType`**: Discrete → Discrete, Continuous → Continuous (new axis types are available).
6. **Use `SchemeId` instead of `u64` identifiers**.

### 7.2 Example: Old vs New

**Old:**
```rust
let scheme = Grid2DScheme::new(10, 10);
let addr = scheme.map_to_memory(&SpaceCoordinates::new(vec![2, 3]));
```

**New:**
```rust
let scheme = Grid2DTemplate::new(10, 10, GridTopology::FourConnected).build();
let addr = scheme.map_to_logical_address(&SpaceCoordinates::new(vec![2, 3]));
```

## 8. Examples

### 8.1 Creating a Custom Scheme with Hierarchical Relations
```rust
let mut builder = SchemeBuilder::new();
builder
    .add_axis(Axis { name: "x".into(), axis_type: AxisType::Discrete, metadata: HashMap::new() })
    .add_axis(Axis { name: "y".into(), axis_type: AxisType::Discrete, metadata: HashMap::new() })
    .add_segment(Segment::new(SpaceCoordinates::new(vec![0, 0])))
    .add_segment(Segment::new(SpaceCoordinates::new(vec![1, 0])))
    .add_relation(
        SegmentId::from_coords(&SpaceCoordinates::new(vec![0, 0])),
        SegmentId::from_coords(&SpaceCoordinates::new(vec![1, 0])),
        StructuralRelation::Hierarchy {
            parent: SegmentId::from_coords(&SpaceCoordinates::new(vec![0, 0])),
            depth: 1,
            relation_type: HierarchyType::Containment,
        }
    )
    .set_memory_layout(MemoryLayout {
        layout_type: LayoutType::RowMajor,
        mapping: Arc::new(|coords| {
            let x = coords.get(0)?;
            let y = coords.get(1)?;
            Some(LogicalAddress { address: vec![*x as u8, *y as u8], metadata: HashMap::new() })
        }),
        metadata: HashMap::new(),
    });
let scheme = builder.build();
```

### 8.2 Composite Scheme with Union
```rust
let grid = Grid2DTemplate::new(5, 5, GridTopology::FourConnected).build();
let line = IntegerLineTemplate::new(0, 10, 1).build();

let composite = CompositeScheme::new(
    vec![SchemeImpl::Basic(grid), SchemeImpl::Basic(line)],
    CompositionRules {
        combination_method: CombinationMethod::Union,
        alignment_rules: AlignmentRules::default(),
        conflict_resolution: ConflictResolution::Priority(vec![0]),
    }
);
```

### 8.3 Applying a Rotation Transformation
```rust
let base = Grid2DTemplate::new(8, 8, GridTopology::EightConnected).build();
let transformed = TransformedScheme::new(
    Box::new(SchemeImpl::Basic(base)),
    Transformation {
        transform_type: TransformType::Rotation { angle_deg: 45.0, center: (4.0, 4.0) },
        parameters: HashMap::new(),
    }
);
```

## 9. Testing the New Abstraction

The proof‑of‑concept includes updated constitutional concept tests (`poc/src/main.rs`) that verify:

1. **Basic Scheme functionality** (`test_scheme_concept`) – uses templates and validates mapping.
2. **Adjacency & Memory Layout** (`test_adjacency_memory`) – tests structural relations and logical‑address mapping.
3. **Composite & Transformed Schemes** (`test_composite_and_transformed_schemes`) – verifies composition and transformation rules.
4. **Transition Matrix** (`test_transition_matrix`) – placeholder for future integration.
5. **Integrated Workflow** (`test_integrated_workflow`) – placeholder for end‑to‑end scenario.

All ten constitutional tests pass after the migration.

## 10. Future Directions

- **Observation‑rule integration**: Connect `ObservationRules` to actual Field projection.
- **Dynamic scheme modification**: Allow incremental updates while preserving cryptographic identity.
- **Physical‑layout mapping**: Bridge logical addresses to concrete memory addresses (e.g., DRAM, HBM, PIM).
- **Serialization/deserialization**: Save/load Schemes from `.ss` files.
- **Optimized graph queries**: Indexed relation lookups for large‑scale Schemes.

## 11. Conclusion

The new Scheme abstraction layer provides a mathematically rigorous, flexible, and future‑proof foundation for SSCCS. By decoupling structure from physical implementation, it enables the same Scheme to be projected onto diverse hardware architectures while maintaining a cryptographically verifiable identity. The addition of composite and transformed schemes opens the door to hierarchical, modular, and dynamically adaptable computational spaces.

---

© 2026 SSCCS gUG (i.G.). This human‑conceived and AI‑refined documentation is licensed under CC BY‑NC‑ND 4.0; authenticity and integrity are cryptographically verifiable via GPG‑signed commits.