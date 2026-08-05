# PoC Diagnosis and Roadmap

2026-08-06

SSCCS Foundation

## Context

This document records the SSCCS Proof-of-Concept (PoC) as specified by the pure model philosophy, written from the point after the new poc specification is implemented. SSCCS is the top-level umbrella project. It is not an extension of existing computing; it stands opposite to it. Computation is the observation of fixed structure under changing conditions, not sequential state mutation, and the thinking itself stays independent of the von Neumann model.

The poc is the pure plane layer. It implements only the crystallized essence of the model and knows no sub-project internals. Sub-projects (tagma, chton, nexus, ev, rem, and external silicon calibrations) are virtual materializations of the philosophy on existing computing; their experience enters the poc only as strengthened primitives through the specification, never as implementation coupling.

Reference documents:

- Main Whitepaper (`/docs/whitepaper/whitepaper.qmd`): the core ontology (Segment, Scheme, Field, Observation, Projection), the compiler pipeline, and the open format appendix.
- Open Format Center (`/docs/notes/open_format/index.qmd`): the center document governing the open format poc track, holding the materialization thesis of the pure plane.
- Projects Index (`/docs/projects/index.qmd`): the two-plane architecture of the ecosystem.

## The Two Planes and the poc Role

The pure plane holds the formal model: the four primitives and the observation semantics, defined from their own axioms. The practical plane holds every project that concretizes one functional region of the paradigm in running code on existing computing. The shared surface between them carries deposits upward as strengthened primitives and scaffolding downward as philosophy.

The poc occupies the pure plane. Its Rust implementation is a reference simulation: the model is emulated on existing hardware only to validate it. The simulation is not the model. This distinction governs every component of the implemented specification.

## Implemented Specification

The new poc specification is implemented. Its components are the simulation vehicle, not the definition; each one realizes one part of the pure model on existing computing:

1. Model semantics formalized: the observation operator is defined as a pure function over a Scheme and a Field. Determinism, statelessness, implicit parallelism, and verifiability are stated as definitional properties of the operator, and the implementation validates against them.
2. Pure open format finalized: the format carries only topology. The header records magic and version, and the body holds Axes, Segments, Relations (adjacency, metric space, boundary conditions), and Observation (trigger, resolution, projection format). No registers, clocks, circuits, memory layout, or instruction flow appear. The Scheme identity is derived from topology only.
3. Parser and serializer implemented: the parser reconstructs a Scheme from a real format document, and the serializer writes a document that round-trips. Every section of the format is handled, including all axis types, relation categories, and observation rules.
4. Real format fixtures created: boolean and integer spaces exist as genuine format documents. The misleading Rust modules that carried a format extension are renamed, and fixtures are generated from the serializer so the format and the implementation cannot drift.
5. Structural analysis implemented: adjacency extraction, hierarchy detection, and independent subgraph identification partition a Scheme into observation units.
6. Memory-layout resolution implemented: the five abstract policies (linear, row-major, column-major, space-filling curve, hierarchical, graph-based) map coordinates to logical addresses, with the sole correctness criterion that structurally adjacent Segments receive proximate logical addresses.
7. Observation Intermediate Representation defined: Segments are nodes and constraints are edges, synthesizable as a structural graph without any execution semantics.
8. Realization recipes produced: CPU observation loops, FPGA data-path, and PIM command sequences, each framed as structural mapping and locality preservation, never as instruction scheduling.
9. Validation extended: golden anchors cover every observation path. Determinism checks repeat observations across admissible configurations, and race-freedom checks run concurrent observations on disjoint regions.
10. Purity gates enforced in CI: the dependency gate and the terminology gate run on every change.

## What the Implementation Validated

The implemented specification demonstrates the pure model on existing computing:

- Observation is deterministic across all admissible configurations of every fixture, and the same Scheme, Field, and time coordinate always produce the same Projection.
- Structurally adjacent Segments receive proximate logical addresses under all five layout policies, confirming the locality criterion is a property of the mapping functions, not of the topology.
- The format round-trips exactly: parse, serialize, and parse again reproduce the identical Scheme.
- The Scheme identity is invariant under physical mapping changes and changes when the connectivity or the metric space changes, as the topological identity rule requires.
- Concurrent observations on disjoint regions complete without locks and reproduce sequential results, confirming implicit parallelism by construction.
- The purity gates pass: the poc workspace carries no sub-project dependency and no sub-project identifier.

## Diagnosis: What Remains

The pure specification is implemented; the reference simulation is not yet complete at the assembly level. The remaining work is the execution layer of the simulation and its hardening:

1. Assembly-level reference simulation: the observation operator and the format pipeline need the assembly-level implementation that turns the validated semantics into concrete machine instructions, as the immediate next phase.
2. Mechanized verification: determinism and race-freedom are validated by testing; formal proofs in a proof assistant remain.
3. Benchmarking as validation: the benchmarking suite exists, but measurements against the von Neumann baseline are not yet collected. The baseline is the von Neumann execution of the same kernel, and measurements inform the practical plane, never the model.
4. Practical plane handoff: the realization recipes are defined but not exercised on concrete substrates. Exercising them belongs to the practical plane projects, which consume the philosophy, not to the poc.
5. Tooling: syntax highlighting and a visualizer for the format are conveniences for the practical plane, not pure plane requirements.

## Roadmap

### Phase 1: Assembly-Level Reference Simulation

Implement the observation operator and the format pipeline at the assembly level. This is the execution layer of the simulation: the validated semantics lowered to concrete machine instructions, with golden anchors preserved across the lowering. The detailed plan is proposed separately.

### Phase 2: Mechanized Verification

Mechanize the determinism proof for a single observation and the commutativity proof for concurrent observations on non-overlapping Segments, and integrate the proofs into the CI pipeline.

### Phase 3: Benchmarking and Validation

Execute the benchmarking suite against the von Neumann baseline and record the measurements as validation evidence. Publish the numbers as deposits on the shared surface for the practical plane.

### Phase 4: Practical Plane Handoff

Release the format specification and the realization recipes to the practical plane. Sub-projects materialize them on their substrates; the poc remains independent of every project it enables.

## Purity Gates

Two gates are enforced in CI. The dependency gate fails if any sub-project crate (tagma, chton, nexus, ev, or their types) appears in the poc workspace dependencies or source. The terminology gate fails if sub-project identifiers (CoordId, FIH, materialization surfaces, verification constraint vocabularies) appear in the poc core. These gates make the umbrella property mechanical: the poc knows no sub-project internals.

## Immediate Next Actions

1. Execute the assembly-level implementation plan for the reference simulation, starting from the observation operator and the pure format pipeline.
2. Begin the mechanized verification work in parallel.
3. Run the benchmarking suite and record the validation measurements.
4. Prepare the practical plane handoff package: format specification, fixtures, and realization recipes.

## Conclusion

The pure specification is implemented and validated: the model semantics, the open format, structural analysis, layout resolution, and the realization recipes all stand on the pure plane, and the purity gates hold. The next step is the assembly-level reference simulation, which turns the validated semantics into concrete machine instructions. The poc remains the independent top-level layer that every project on the practical plane inherits from.
