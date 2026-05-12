# Scheme Public API Audit

Generated: 2026-05-12T13:21:47Z

## Summary

| Method | [BUILD] | [COMPILE] | [OBSERVE] | [DIAGNOSTIC] | Total |
|--------|---------|-----------|-----------|--------------|-------|
| get_segment | 1 | 0 | 0 | 0 | 1 |
| segments | 1 | 1 | 2 | 1 | 5 |
| segment_ids | 0 | 0 | 0 | 0 | 0 |
| structural_neighbors | 0 | 0 | 1 | 1 | 2 |
| axes | 0 | 0 | 0 | 2 | 2 |
| dimensionality | 1 | 0 | 1 | 2 | 4 |
| map_to_logical_address | 0 | 1 | 0 | 2 | 3 |
| validate_structure | 0 | 0 | 0 | 1 | 1 |
| id | 2 | 0 | 0 | 3 | 5 |

## Detailed Call Sites

### `get_segment()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/schemes/src/composite.rs` | 130 | `CompositeScheme::get_segment()` delegates to `c.get_segment(segment_id)` on each component | [BUILD] |

### `segments()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/primitive/src/scheme/abstract_scheme.rs` | 220 | `Grid2DTemplate::build()` calls `SchemeBuilder::add_segments()` followed by `.build()`, indirectly consuming `segments()` from `Scheme` | [BUILD] |
| `poc/standard/crates/examples/src/compiler_pipeline.rs` | 74 | `stage_memory_layout_resolution()` iterates over `self.scheme.segments()` to resolve logical addresses | [COMPILE] |
| `poc/standard/crates/experiments/integrated/src/main.rs` | 15 | `test_integrated_workflow()` calls `scheme.segments().count()` to print segment count | [OBSERVE] |
| `poc/standard/crates/experiments/integrated/src/main.rs` | 29 | `test_integrated_workflow()` calls `scheme.segments().find(...)` to locate a segment for observation | [OBSERVE] |
| `poc/standard/crates/experiments/data-processing/src/main.rs` | 130,150 | `main()` iterates over `scheme.segments()` in the SSCCS observation loop | [OBSERVE] |
| `poc/standard/crates/experiments/scheme/src/main.rs` | 30 | `test_scheme_concept()` calls `grid_scheme.segments().count()` for diagnostic printing | [DIAGNOSTIC] |

### `structural_neighbors()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/experiments/integrated/src/main.rs` | 35 | `test_integrated_workflow()` calls `scheme.structural_neighbors(segment.id(), None)` during observation simulation | [OBSERVE] |
| `poc/standard/crates/experiments/adjacency/src/main.rs` | 91 | `test_adjacency_memory()` calls `scheme.structural_neighbors(seg1.id(), None)` in test verification | [DIAGNOSTIC] |

### `axes()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/experiments/scheme/src/main.rs` | 31 | `test_scheme_concept()` calls `grid_scheme.axes().len()` for diagnostic printing | [DIAGNOSTIC] |
| `poc/standard/crates/experiments/composite/src/main.rs` | 58 | `test_composite_and_transformed_schemes()` calls `composite.axes()` and prints axes count | [DIAGNOSTIC] |

### `dimensionality()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/primitive/src/scheme/abstract_scheme.rs` | 169 | `Scheme::dimensionality()` returns `self.axes.len()` (definition, not a call site) | [BUILD] |
| `poc/standard/crates/experiments/integrated/src/main.rs` | 46 | `test_integrated_workflow()` calls `scheme.dimensionality()` inside `assert_eq!` | [DIAGNOSTIC] |
| `poc/standard/crates/experiments/scheme/src/main.rs` | 29 | `test_scheme_concept()` calls `grid_scheme.dimensionality()` for diagnostic printing | [DIAGNOSTIC] |
| `poc/standard/crates/experiments/composite/src/main.rs` | 68 | `test_composite_and_transformed_schemes()` calls `transformed.dimensionality()` inside `assert_eq!` | [DIAGNOSTIC] |

### `map_to_logical_address()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/examples/src/compiler_pipeline.rs` | 77 | `stage_memory_layout_resolution()` calls `self.scheme.map_to_logical_address(coords)` to compute logical addresses for each segment | [COMPILE] |
| `poc/standard/crates/experiments/scheme/src/main.rs` | 37 | `test_scheme_concept()` calls `grid_scheme.map_to_logical_address(&test_coords)` in test | [DIAGNOSTIC] |
| `poc/standard/crates/experiments/adjacency/src/main.rs` | 96 | `test_adjacency_memory()` calls `scheme.map_to_logical_address(&coords)` in test verification | [DIAGNOSTIC] |

### `validate_structure()`

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/experiments/scheme/src/main.rs` | 48 | `test_scheme_concept()` calls `int_scheme.validate_structure(&valid_coords)` in test | [DIAGNOSTIC] |

### `id()` (on Scheme)

| File | Line | Context | Classification |
|------|------|---------|---------------|
| `poc/standard/crates/schemes/src/composite.rs` | 49 | `CompositeScheme::new()` calls `component.id().as_bytes()` for cryptographic ID derivation | [BUILD] |
| `poc/standard/crates/schemes/src/composite.rs` | 105 | `TransformedScheme::new()` calls `base.id().as_bytes()` for cryptographic ID derivation | [BUILD] |
| `poc/standard/crates/experiments/scheme/src/main.rs` | 27 | `test_scheme_concept()` calls `grid_scheme.id().as_bytes()` for hex printing | [DIAGNOSTIC] |
| `poc/standard/crates/experiments/composite/src/main.rs` | 49 | `test_composite_and_transformed_schemes()` calls `composite.id().as_bytes()` for hex printing | [DIAGNOSTIC] |
| `poc/standard/crates/experiments/composite/src/main.rs` | 65 | `test_composite_and_transformed_schemes()` calls `transformed.id().as_bytes()` for hex printing | [DIAGNOSTIC] |

## Analysis

### Legitimate [BUILD] Sites

All construction-time call sites appear in three locations:

- **`SchemeBuilder::build()` / `Scheme::new()`** in `abstract_scheme.rs` -- the canonical construction path.
- **`CompositeScheme::new()`** in `composite.rs` -- calls `component.id()` only for hashing inputs.
- **`TransformedScheme::new()`** in `composite.rs` -- calls `base.id()` only for hashing inputs.

These are legitimate because the Scheme is being assembled and its cryptographic identity derived before any runtime use.

### Legitimate [COMPILE] Sites

- **`CompilerPipeline::stage_memory_layout_resolution()`** in `compiler_pipeline.rs` calls `segments()` and `map_to_logical_address()`. This is a compile-time transformation that resolves abstract memory layouts to logical addresses, a purely structural operation with no observation-time semantics.

### [OBSERVE] Sites -- Potential Principle Violations

- **`test_integrated_workflow()`** in `experiments/integrated/src/main.rs` calls `segments()`, `structural_neighbors()`, and `dimensionality()` in a function that simulates runtime observation. The calls to `segments().find()` and `structural_neighbors()` occur inside the observation simulation path and constitute direct Scheme access at observation time.
- **`main()`** in `experiments/data-processing/src/main.rs` iterates over `scheme.segments()` in its observation loop, repeatedly accessing Scheme elements during runtime observation.

These sites warrant review to determine whether a stricter interface (e.g., restricting observation-time access to `Segment` handles only) should be enforced.

### [DIAGNOSTIC] Sites

All remaining call sites occur inside `describe()`, `Display`-equivalent printing, `assert_eq!` checks, or test verification steps. These are acceptable for developer tooling.

## Recommendations

1. **Refactor observation loops** in `data-processing/src/main.rs` and `integrated/src/main.rs` to receive pre-resolved `Segment` handles rather than calling `scheme.segments()` at observation time.
2. **Encapsulate `structural_neighbors()`** behind a compile-time facade if it is only needed before runtime.
3. **No action required** for [BUILD], [COMPILE], or [DIAGNOSTIC] sites -- these follow the intended architecture.
