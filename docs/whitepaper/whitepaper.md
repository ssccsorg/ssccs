# Schema–Segment Composition Computing System
Taeho Lee
February, 2026

``` python
title_meta_items = {
   "html": [
      {"title": "Other Formats", "link": "https://docs.ssccs.org/whitepaper.pdf", "content": "PDF", "content_class": "bi bi-file-pdf"},
      {"title": "View Slides", "link": "https://docs.ssccs.org/proposal/pt.pdf", "content": "PDF", "content_class": "bi bi-file-pdf"},
  ]
}
```

## Abstract

SSCCS (Schema–Segment Composition Computing System) is an
observation-driven computing model that defines deterministic
computation as the realization of structured potential under dynamic
constraints. In an era of increasing complexity and distributed systems,
this contrasts with the traditional von Neumann approach of instruction
sequencing, state mutations, and data
movement[\[1\]](#ref-horowitz2014computing) between memory and
processor, and the compiler’s role shifts from translating code to
optimizing the topology of data movement. This model treats time as
merely one axis of multi-dimensional computation rather than an absolute
sequence, with inherent structural isolation against interference and
lossless interpretation via a Geometric Manifold.

Computation is formalized as the deterministic projection of immutable
Segments and Schemes within dynamic Fields. Acting as mutable constraint
units, Fields enable recursive composition and allow governance logic to
be encrypted or sandboxed at the binary level. The compiler performs
structural mapping, embedding logic directly into hardware topology to
ensure stationary data (Logic-at-Rest) and minimize movement. This
design innovation mitigates data movement overhead and enables inherent
parallelism, targeting dramatic improvements in performance and energy
efficiency. Security and cryptographic auditability are geometrically
natural consequences of this immutable structure, rather than added
features.

As a universal substrate, SSCCS provides a verifiable foundation for
systems across domains—from AI to scientific computing to embedded
systems. Driven by a software-first philosophy, this specification
provides a roadmap where logical design dictates physical
implementation, contrasting with current hardware advances that focus
primarily on physical improvements. Ultimately, SSCCS aims to evolve
into an open format
\[*<a href="#sec-appendix-openformat" class="quarto-xref">13</a>*\] at
the language layer, transitioning logic into a transparent, accessible,
and energy-efficient Intellectual Public Commons.

## Philosophical Foundation

**Loops disappear into layout. Data, or state, is the shadow cast by
collapsed possibility:** A System where Structured Deployment is the
Path, and Observed Synthesis is the Computation

Beneath immutable segments and schemes, observation momentarily
activates the Field, precipitating the collapse of possibility and
giving rise to a projection. A projection, as the residue of collapse,
is transient; it constitutes what we recognize as data or state. Yet
throughout this entire process, the fundamental structure itself remains
untouched and unaltered.



------------------------------------------------------------------------

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research
initiative, formalized through global standards and substantiated by its
cryptographic authenticity.

- Whitepaper: [PDF](https://ssccs.org/wp) /
  [HTML](https://ssccs.org/wpw) DOI:
  [10.5281/zenodo.18759106](https://doi.org/10.5281/zenodo.18759106) via
  CERN/Zenodo, indexed by OpenAIRE. Licensed under *CC BY-NC-ND 4.0*.
- Official repository: [GitHub](https://github.com/ssccsorg).
  Authenticated via GPG:
  [BCCB196BADF50C99](https://keys.openpgp.org/search?q=BCCB196BADF50C99).
  Licensed under *Apache 2.0*.
- Governed by the [Foundational Charter and
  Statute](https://ssccs.org/legal) of the SSCCS Foundation (in
  formation).
- Provenance: Human-authored and AI-refined: linguistic and editorial
  review; full intellectual responsibility with author(s). All major
  outputs are [C2PA-certified](https://ssccs.org/wpc2pa).

------------------------------------------------------------------------





## Introduction

SSCCS redefines computation through four primitives: **Segments**
(immutable points), **Schemes** (immutable blueprints), **Fields**
(mutable constraints), and **Observation** (the active event). This
redefinition yields deterministic reproducibility: because the structure
is fixed and observation is deterministic, every computation produces a
verifiable trace from blueprint to projection.

<div id="fig-ontology">

``` python
dot("""
digraph SSCCS_Ontology {
    rankdir=TB;
    nodesep=0.5;

    node [style=invis, label="", width=3, height=0.1]; 
    spacer_l; spacer_r;

    node [shape=rect, style=filled, fillcolor=white, color=black, fontsize=10];

    // Static Infrastructure
    node [shape=point, width=0.2, height=0.2, fillcolor=black, color=black, style=solid];
    s1 [xlabel="Segment 1(S₁)\\nNOT USED"];
    s2 [xlabel="Segment 2(S₂)"];
    s3 [xlabel="Segment 3(S₃)"];
    
    // Structural Blueprint & Others
    node [shape=rect];
    Scheme [label="Scheme (Σ₁)"];
    Field [label="Field (F₁)\\ngovernance, constraints, ..."];
    Observation [label="Observation (Ω₁)", shape=ellipse];
    Projection [label="Projection (P₁)\\n", shape=box];
    Data [label="Actualized Possibility: State, or Data (D₁)\\nD₁ = I₁(P₁)", shape=box, style=rounded];
    
    { rank=same; spacer_l; Field; spacer_r; }

    {rank=source;
        edge [arrowhead=none, style=solid];
        Scheme -> s2;
        Scheme -> s3;
    }
    
    edge [arrowhead=normal];
    Scheme -> Field;
    s2 -> Field;
    s3 -> Field;

    edge [arrowhead=normal, style=solid];
    Observation -> Field [label="Ω: Computation Event"];
    
    Field -> Projection [label="P₁ = Ω₁(F(Σ(S₂,S₃)))"];
    Projection -> Data [label="Interpretion (I₁)"];

    edge [style=invis];
    spacer_l -> Field;
    Field -> spacer_r;
}
""")
```

Figure 1

</div>

For decades, computation has been defined by the von Neumann model:

This formulation rests on several assumptions: data exists as intrinsic
values in memory, programs are instruction sequences, and execution
involves moving data between memory and processor across a sequential
timeline. These assumptions are not fundamental laws but consequences of
a specific architectural choice. Consequently, the majority of energy
and time in conventional systems is spent on data movement rather than
logic—a symptom known as the “data-movement wall”
[\[1\]](#ref-horowitz2014computing), [\[2\]](#ref-wulf1995hitting),
[\[3\]](#ref-borkar2011future), [\[4\]](#ref-lucas2014top).

While new hardware-side paradigms attempt to mitigate this, they remain
localized optimizations within the same sequential paradigm. SSCCS
proposes a shift from procedural execution to **structural
observation**:

Simply put, the Field governs the observation of the Scheme and its
Segments, producing a Projection that can be interpreted as data. Each
layer has defined properties and relationships; together they form the
complete computational model.

<div id="fig-ssccs-multifield">

``` python
dot("""
digraph SSCCS_MultiField {
    node [shape=rect];
    graph [pad="0.5, 0"];
    
    // === Leftmost rank: Segments and Schemes (immutable) ===
    { rank=source;
        // Segments (atomic coordinates)
        node [shape=point, width=0.2, height=0.2];
        s1 [xlabel="S₁"];
        s2 [xlabel="S₂"];
        s3 [xlabel="S₃"];
        s4 [xlabel="S₄"];
        s5 [xlabel="S₅"];
        s6 [xlabel="S₆"];
        s7 [xlabel="S₇"];
        s8 [xlabel="S₈"];
        
        // Schemes (structural blueprints)
        node [shape=box, style=solid];
        sch1 [label="Σ₁"];
        sch2 [label="Σ₂"];
        sch3 [label="Σ₃"];
        sch4 [label="Σ₄"];
    }
    
    // === Second rank: Fields (dynamic governance) ===
    { rank=2;
        node [shape=rect, style=dashed];
        f1 [label="F₁"];
        f2 [label="F₂"];
        f3 [label="F₃"];
    }
    { rank=same; f1; f2; f3; }
    
    // === Third rank: Observation events ===
    { rank=3;
        node [shape=ellipse];
        o1 [label="Ω₁"];
        o2 [label="Ω₂"];
        o3 [label="Ω₃"];
        o4 [label="Ω₄"];
        o5 [label="Ω₅"];
    }
    { rank=same; o1; o2; o3; o4; o5; }
    
    // === Fourth rank: Projections (manifested states) ===
    { rank=4;
        node [shape=box];
        p1 [label="P₁"];
        p2 [label="P₂"];
        p3 [label="P₃"];
        p4 [label="P₄"];
        p5 [label="P₅"];
    }
    { rank=same; p1; p2; p3; p4; p5; }
    
    // === Fifth rank: Interpreted Data (final deterministic values) ===
    { rank=5;
        node [shape=box, style=rounded];
        d1 [label="D₁\\n= I₁(P₁)"];
        d2 [label="D₂\\n= I₂(P₂)"];
        d3 [label="D₃\\n= I₃(P₃)"];
        d4 [label="D₄\\n= I₄(P₄)"];
        d5 [label="D₅\\n= I₅(P₅)"];
    }
    { rank=same; d1; d2; d3; d4; d5; }
    
    // === Scheme–Segment structural relations (undirected lines) ===
    edge [arrowhead=none, style=solid];
    sch1 -> s1; sch1 -> s2; sch1 -> s3;
    sch2 -> s2; sch2 -> s4; sch2 -> s5; sch2 -> s6;
    sch3 -> s3; sch3 -> s5; sch3 -> s7; sch3 -> s8;
    sch4 -> s1; sch4 -> s4; sch4 -> s6; sch4 -> s8;
    
    // === Field influences on Schemes and Segments (dashed) ===
    edge [arrowhead=none, style=dashed];
    f1 -> sch1; f1 -> sch2; f1 -> s1; f1 -> s2; f1 -> s4;
    f2 -> sch2; f2 -> sch3; f2 -> s3; f2 -> s5; f2 -> s7;
    f3 -> sch3; f3 -> sch4; f3 -> s6; f3 -> s8;
    
    // === Structural input: Schemes and Segments define Field boundaries (solid) ===
    edge [arrowhead=normal, style=solid];
    sch1 -> f1; sch2 -> f1; sch2 -> f2; sch3 -> f2; sch3 -> f3; sch4 -> f3;
    s1 -> f1; s2 -> f1; s3 -> f2; s4 -> f1; s5 -> f2; s6 -> f3; s7 -> f2; s8 -> f3;
    
    // === Trigger mechanism: Each Observation applies to a Field ===
    edge [arrowhead=normal, style=solid];
    o1 -> f1 [label="Ω"];
    o2 -> f1 [label="Ω"];
    o3 -> f2 [label="Ω"];
    o4 -> f2 [label="Ω"];
    o5 -> f3 [label="Ω"];
    
    // === Field manifests Projection under observation ===
    f1 -> p1 [label="P₁ = Ω₁(F₁)"];
    f1 -> p2 [label="P₂ = Ω₂(F₁)"];
    f2 -> p3 [label="P₃ = Ω₃(F₂)"];
    f2 -> p4 [label="P₄ = Ω₄(F₂)"];
    f3 -> p5 [label="P₅ = Ω₅(F₃)"];
    
    // === Interpretation: Projection yields deterministic Data ===
    edge [arrowhead=normal, style=solid];
    p1 -> d1 [label="I₁"];
    p2 -> d2 [label="I₂"];
    p3 -> d3 [label="I₃"];
    p4 -> d4 [label="I₄"];
    p5 -> d5 [label="I₅"];
}
"""
)
```

Figure 2

</div>

Through immutable Segments and Schemes, SSCCS achieves emergent
parallelism without locks, eliminates data movement via structural
mapping, and ensures deterministic results. Observation events can occur
concurrently without temporal ordering, and the resulting projections
are independent. **Time is not a fundamental dimension that governs
state changes**; instead, the structure of Schemes and the constraints
of Fields govern what can be observed and when.

### Segment: Atomic Coordinate Existence

Let $\mathcal{S}$ denote the set of all Segments. A Segment
$s \in \mathcal{S}$ is a tuple $(c, id)$ where $c \in \mathbb{R}^d$
represents coordinates in a $d$-dimensional possibility space, and
$id = H(c)$ is a cryptographic hash providing a unique identifier.

Its properties are: **Immutability** (once created, a Segment cannot be
modified), **Statelessness** (contains no values, only coordinates and
identity). Because Segments contain no mutable state, they can be
observed concurrently by any number of observers without
synchronization. The cryptographic identity ensures that every Segment
is uniquely identifiable.

### Scheme: Structural Blueprint

A Scheme $\Sigma$ is an immutable blueprint that defines the structural
relationships-a geometric arrangement of Segments, not a sequence of
operations. Segment relationships are spatial rather than temporal.
During compilation, the compiler maps these spatial relationships
directly to hardware addresses, ensuring that structurally adjacent
Segments become physically adjacent. This design makes locality an
inherent property of the specification, eliminating the need for runtime
optimizations.

Formally, $\Sigma = (A, R, L, O)$ where:

- $A = \{a_1, \dots, a_k\}$ is a set of axes, each axis
  $a_i = (\text{name}_i, \text{type}_i)$ with
  $\text{type}_i \in \{\text{Discrete}, \text{Continuous}, \text{Cyclic}, \text{Categorical}, \text{Relational}, \text{WithUnit}\}$.
- $R \subseteq \mathcal{S} \times \mathcal{S} \times \mathcal{T}$ is a
  set of structural relations, where $\mathcal{T}$ denotes relation
  types (Adjacency, Hierarchy, Dependency, Equivalence, Custom).
- $L: \mathbb{R}^d \to \mathcal{L}$ is a memory‑layout mapping that
  assigns each coordinate a logical address.
- $O = (\text{resolution}, \text{triggers}, \text{priority}, \text{context})$
  are observation rules that govern how observations are resolved,
  triggered, prioritized, and contextualized.

### Field: Dynamic Constraint Substrate

The Field $F$ is the only mutable layer, but it does not store values.
Instead, it stores admissibility conditions that dynamically constrain
which configurations of Segments are possible at any given time.
Formally, $F = (C, T)$ where:

- $C: \mathcal{S} \to \mathbb{B}$ is a constraint predicate (or a set of
  admissible coordinates).
- $T: \mathcal{S} \times \mathcal{S} \to \mathbb{R}$ is a transition
  matrix that assigns weights to possible transitions between Segments.

Mutating $F$ changes which configurations are possible, but does not
modify any Segment.

### Observation and Projection

The observation operator $\Omega$ is the single active event that
produces a projection from a Scheme and a Field:

$$P = \Omega(\Sigma, F).$$

Let
$\mathcal{A}(\Sigma, F) = \{ s \in \mathcal{S} \mid C(s) = \text{true} \}$
be the set of Segments admissible under the Field’s constraints. The
observation operator selects a projection $P$ according to the
resolution strategy specified in $O$. For each admissible segment $s$,
the projection $P(s)$ is given by a projector $\pi$ that encodes the
semantic interpretation of the Field and Segment:

$$P(s) = \pi(s, F) \quad \text{for } s \in \mathcal{A}(\Sigma, F).$$

If the resolution strategy is deterministic, $\Omega$ is a function; if
probabilistic, it samples from a distribution defined by the transition
weights $T$. Observation occurs when the structure and Field together
create an instability—i.e., multiple admissible configurations. $\Omega$
deterministically selects one configuration and returns it as $P$. No
data is moved during observation; Segments remain in place.

### Structural Isolation

Security properties emerge from the immutable structure rather than
being added features. Since Segments cannot be modified, concurrent
observations are naturally isolated. Formally, for any two disjoint sets
of Segments $S_1$ and $S_2$,

$$\Omega(S_1 \cup S_2, F) = \Omega(S_1, F) \times \Omega(S_2, F),$$

where $\times$ denotes independent composition of projections. Every
Segment and Scheme has a unique cryptographic hash, enabling
identity‑based boundaries where computations can only access Segments
for which they hold valid references. This provides inherent structural
isolation against interference without requiring additional security
mechanisms.

### Relationship with Traditional Concepts

| Traditional Concept | SSCCS Counterpart | Shift |
|----|----|----|
| Instruction fetch | Not applicable | No imperative control flow |
| Operand load | Segment coordinates | Data never moves; only observed |
| Result store | Projection (ephemeral) | Results are events, not states |
| Cache line fill | Structural layout | Locality from geometry |
| Lock acquisition | Immutability | No shared mutable state |
| Program counter | Coordinate dimension | Time as coordinate |
| Algorithm | Geometry | Structure determines observation |

## Formal Properties

### Energy Model

A formal energy model for SSCCS can be expressed as:

$$E_{\text{total}} = E_{\text{obs}} \cdot N_{\text{obs}} + E_{\text{update}} \cdot N_{\text{update}},$$

where $E_{\text{obs}}$ is the energy required to perform a single
observation, $E_{\text{update}}$ is the energy required to mutate the
Field, $N_{\text{obs}}$ is the number of observations, and
$N_{\text{update}}$ is the number of field updates. There is no term for
moving data between memory and processor, because Segments are
stationary. This model predicts that energy consumption scales with the
number of observations and field updates, but not with data movement,
which is a key source of energy inefficiency in traditional
architectures [\[1\]](#ref-horowitz2014computing).

### Immutability and Concurrency

Because Segments are immutable, any number of observations can be
performed simultaneously without interference. Formally, if $S_1$ and
$S_2$ are disjoint sets of Segments, then:

$$\Omega(S_1 \cup S_2, F) = \Omega(S_1, F) \times \Omega(S_2, F)$$

where $\times$ denotes independent composition of projections. This
property follows directly from the absence of shared mutable state:
since Segments cannot be modified, observations on disjoint sets have no
side‑effects that could affect each other. Consequently, SSCCS enables
inherent parallelism without any programmer effort or runtime
synchronisation.

### Time as a Coordinate

Time is treated as one coordinate axis among many. Let
$t \in \mathbb{R}$ be a coordinate along the time axis; the Scheme may
define $t$ as a continuous axis or as a cyclic axis with period $\tau$
(i.e., $t \equiv t \mod \tau$). Temporal ordering is expressed by
comparing coordinates along that axis. Observations do not have a global
temporal order unless explicitly defined. This eliminates the notion of
a “program counter” and the associated assumption that computation must
proceed in sequence.

### Determinism and Auditability

Observation is deterministic: for identical $\Sigma$ and $F$, $\Omega$
always yields the same $P$. This follows from the definition of $\Omega$
as a function of $\Sigma$ and $F$; any non‑determinism must be
explicitly introduced through the resolution strategy in $O$.
Determinism enables auditability as a secondary benefit: every
projection is a verifiable trace from blueprint to output. However, this
is a consequence of the core structural properties, not a primary design
goal.

## Compilation and Structural Mapping

A key engineering contribution of SSCCS is that the compiler, rather
than generating a sequence of instructions, performs structural mapping
of the Schema onto the target hardware. The compiler analyses the
adjacency relations and memory layout semantics declared in the Schema
written in the open format(`.ss`)
\[*<a href="#sec-appendix-openformat" class="quarto-xref">13</a>*\] and
produces a physical placement of Segments that maximises locality.

For example, if a Schema defines a two-dimensional grid of Segments with
nearest-neighbour adjacency, the compiler can lay out those Segments in
memory in row-major or column-major order such that adjacent Segments
occupy adjacent cache lines. This is analogous to data layout
optimisations performed manually in high-performance computing, but here
it is automated and guaranteed by the Schema’s specification.

<div id="fig-compilation-process">

``` python
dot("""
digraph Compilation_Process {
    rankdir=TB;
    node [shape=rect, style=rounded];
    
    Schema [label="Schema"];
    Hardware [label="Hardware Layout"];
    
    subgraph cluster_compiler {
        label="Compiler";
        style=rounded;
        
        { rank=same; Parse; Analysis; Layout; Map; CodeGen; }
        
        Parse [label="1. Parsing\\n & Validation"];
        Analysis [label="2. Structural\\nAnalysis"];
        Layout [label="3. Memory-Layout\\nResolution"];
        Map [label="4. Hardware\\nMapping"];
        CodeGen [label="5. Observation-Code\\nGeneration"];
        
        Parse -> Analysis -> Layout -> Map -> CodeGen;
    }
    
    Schema -> Parse;
    CodeGen -> Hardware [label="emit layout & code"];
}
"""
)
```

Figure 3

</div>

### Compiler Pipeline

The SSCCS compiler transforms a high-level schema into a
hardware-specific layout through a deterministic pipeline.

1.  **Parsing and Validation**: The `.ss` file is parsed into an
    intermediate representation (IR). Cryptographic identities
    (SchemaId, SegmentId) are computed and verified.
2.  **Structural Analysis**: The compiler extracts adjacency and
    dependency relations. It identifies independent sub-graphs that can
    be observed concurrently.
3.  **Memory-Layout Resolution**: Using the Schema’s `MemoryLayout`
    specification, the compiler resolves the mapping from coordinate
    space to logical addresses. This stage produces a logical address
    map that preserves locality.
4.  **Hardware Mapping**: The logical address map is projected onto the
    target hardware’s physical memory hierarchy. The compiler considers
    cache-line boundaries and, **where available**, processing-in-memory
    (PIM) capabilities to place Segments such that structurally adjacent
    Segments reside in physically proximate storage locations. This
    mapping strategy applies across conventional von Neumann hardware
    (Phase 1-2) and native observation-centric processors (Phase 3),
    with PIM treated as an optional transitional substrate.
5.  **Observation-Code Generation**: For each sub-graph, the compiler
    emits native code that implements the observation operator `Ω`.

The entire pipeline is deterministic and reproducible: given the same
specification and target hardware profile, the compiler always produces
the same layout and observation code.

### Memory Mapping Logic

The compiler’s ability to eliminate data movement hinges on the
`MemoryLayout` abstraction. A `MemoryLayout` consists of a `layout_type`
(e.g., `RowMajor`, `SpaceFillingCurve`), a `mapping` function, and
`metadata`.

A logical address is an intermediate representation: a segment
identifier and an offset within that segment’s conceptual address space.
It is not a physical address; rather, it serves as an intermediate
coordinate that the hardware mapper later translates to concrete
physical locations.

Example: For a 2D grid with row-major layout:
$$f(x, y) = (\text{grid\_id},\; y \cdot \text{width} + x)$$

The compiler evaluates this function for every coordinate in the Schema,
producing a complete logical-address map.

### Embedding Schema into Hardware Topologies

The logical address space acts as a virtualisation layer, decoupling
structural description from physical implementation. The same Schema can
be embedded into vastly different hardware substrates:

- **CPU Caches/DRAM**: High-adjacency Segments map to contiguous cache
  lines.
- **FPGA Block RAM**: The mapping becomes a hardwired address decoder.
- **HBM**: Segments distribute across independent memory channels.
- **Emerging Non-volatile Memories (ReRAM, PCM)**: SSCCS treats the
  physical array as a static coordinate manifold, enabling direct
  structural projection.

Crucially, even on conventional von Neumann hardware, SSCCS overlays a
structural interpretation: the compiler translates logical addresses
into standard load/store operations, but the overall computation remains
free of data movement because all necessary data is already resident
where observation occurs.

### Implementation Cases

- **Vector Addition Example**: A concrete walkthrough of vector addition
  in SSCCS, demonstrating zero data movement and implicit parallelism.
  \[*<a href="#sec-appendix-vector" class="quarto-xref">10</a>*\]
- **Scaling to N‑Dimensional Tensors**: Extension of principles to
  higher‑dimensional structures, featuring zero‑copy reshaping and
  logical adjacency.
  \[*<a href="#sec-appendix-tensor" class="quarto-xref">11</a>*\]
- **Complex Graph Processing**: Application of graph algorithms,
  eliminating pointer chasing through parallel observation.
  \[*<a href="#sec-appendix-graph" class="quarto-xref">12</a>*\]

## Theoretical Performance & Scalability

The SSCCS architecture derives its efficiency not from incremental
hardware acceleration, but from a fundamental shift in computational
complexity.

### Architectural Expectations of Time-Space Complexity

Traditional procedural models are constrained by the linear relationship
between data volume ($N$) and execution cycles. SSCCS decouples this
relationship by utilizing the concurrent propagation of a Field across a
pre-defined Topology.

<div id="fig-complexity">

``` python
import matplotlib.pyplot as plt
import numpy as np

N = np.geomspace(1, 1024, 100)
latency_procedural = N * 1.2 + 5
latency_ssccs = np.log2(N) + 2
movement_procedural = N**1.15
movement_ssccs = np.ones_like(N) * 10 + (N * 0.1)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.plot(N, latency_procedural, color='gray', linestyle='--', label=r'Procedural: $O(N)$')
ax1.plot(N, latency_ssccs, color='gray', linewidth=2, label=r'SSCCS: $O(\log N)$')
ax1.set_xscale('log')
ax1.set_yscale('log')
ax1.set_title('Execution Latency (Time)', fontweight='bold')
ax1.set_xlabel(r'Scale of Data ($N$)')
ax1.set_ylabel('Cycles (Log Scale)')
ax1.legend()

ax2.plot(N, movement_procedural, color='gray', linestyle='--', label=r'Procedural: $O(N \cdot D)$')
ax2.plot(N, movement_ssccs, color='black', linewidth=2, label=r'SSCCS: $O(Projection)$')
ax2.set_xscale('log')
ax2.set_yscale('log')
ax2.set_title('Data Movement (Energy/Space)', fontweight='bold')
ax2.set_xlabel(r'Scale of Data ($N$)')
ax2.set_ylabel('Transfer Volume (Log Scale)')
ax2.legend()

plt.tight_layout()
plt.show()
```

Figure 4

</div>

#### Temporal Complexity (Latency)

In a von Neumann environment, latency scales at $O(N)$ or $O(N/k)$ due
to instruction dispatch and synchronization.

- **SSCCS Latency**: Defined by the physical propagation delay of the
  Field across the Scheme. The observation of the result theoretically
  approaches $O(1)$ in emerging hardware paradigms such as
  Processing-In-Memory (PIM).

#### Data Movement Complexity (Spatial/Energy Cost)

The primary energy sink in modern computing is the movement of operands
from memory to logic units.

- **Procedural Cost**: $O(N \cdot D)$.
- **SSCCS Cost (Logic-at-Rest)**: $O(Projection)$. Since the input
  Segments remain stationary, the energy expenditure is strictly limited
  to the transmission of the resulting Projection.

### Comparative Complexity Matrix

| Metric | Sequential | Parallel (SIMD/GPU) | SSCCS (Structural) |
|----|----|----|----|
| Instruction Overhead | High ($O(N)$) | Moderate ($O(N/k)$) | Minimal (Field-based) |
| Data Locality | Managed (Cache) | Explicit (SRAM/Tiling) | Intrinsic (Scheme-defined) |
| Execution Latency | $O(N)$ | $O(N/k) + \text{sync}$ | $O(\log N)$ or $O(1)$ |
| Data Movement | $O(N)$ | $O(N)$ | $O(\text{Output Only})$ |
| Scalability Limit | Amdahl’s Law | Memory Bandwidth | Physical Propagation Delay |

### Scalability in High-Dimensional AI Workloads

As demonstrated in the emergence of State-Space Models (SSMs)
[\[5\]](#ref-gu2023mamba) and manifold-constrained learning
[\[6\]](#ref-deepseek2025manifold), the ability to process
high-dimensional representations without exhaustive data shuffling is
critical.

1.  **Stationary Topology**: By fixing the Segments in a k-dimensional
    `MemoryLayout`, SSCCS allows the hardware to perform “Observation”
    as a near-instantaneous mapping.
2.  **Implicit Parallelism**: Unlike threads or warps that require
    explicit management, SSCCS parallelism is implicit—it is a property
    of the structure itself.

## System Stack and Instruction-Set Interaction

SSCCS inserts a runtime layer between application and hardware that
translates observation requests into hardware-specific memory mappings.

<div id="fig-system-stack">

``` python
dot("""
digraph SystemStack {
    rankdir=TB;
    node [shape=rect, style=rounded];
    
    // Application Layer
    App [label="Application"];
    
    // Runtime Layer
    subgraph cluster_runtime {
        label="SSCCS Runtime (Observation Manager)";
        style=rounded;
        Runtime [label="Runtime Core\n(Observation Manager)"];
        LayoutCache [label="Layout Cache\n(pre-computed)", style=dashed];
        Projector [label="Projector\n(Ω)"];
    }
    
    // Hardware Layer
    CPU [label="CPU / ISA"];
    RAM [label="RAM / Cache"];
    PIM [label="PIM Unit\n(optional)"];
    
    // Compiler (separate phase)
    subgraph cluster_compiler {
        label="Compiler (Build Time)";
        style=dashed;
        Compiler [label="SSCCS Compiler\n(Structural Mapping)", shape=rect];
    }
    
    // Application to Runtime
    App -> Runtime [label="observe(scheme, field)"];
    
    // Runtime internal
    Runtime -> LayoutCache [label="load layout", style=dashed];
    Runtime -> Projector [label="execute Ω"];
    
    // Runtime to Hardware
    Projector -> CPU [label="observation micro-ops", style=dashed];
    Projector -> PIM [label="in-memory observation", style=dashed];
    
    // Hardware memory access
    CPU -> RAM [label="load/store (minimal)"];
    PIM -> RAM [label="direct access"];
    
    // Compiler output
    Compiler -> LayoutCache [label="emit layout", style=dashed];
    Compiler -> Projector [label="emit observation code", style=dashed];
    
    // Optional: Compiler reads hardware profiles
    Compiler -> CPU [label="target profile", style=dashed, constraint=false];
    Compiler -> PIM [label="target profile", style=dashed, constraint=false];
}
"""
)
```

Figure 5

</div>

### Future Hardware Considerations

While SSCCS can be implemented in software, its benefits are most
pronounced with hardware support:

- No instruction fetch unit; observation triggered structurally.
- Processing-in-memory (PIM) for direct observation.
- Spatial computation mapping adjacency to wiring.

## Related Work

Although SSCCS was developed without direct reference to prior work, its
theoretical core reveals meaningful parallels with several established
research domains:

- **Dataflow architectures** treat programs as graphs where nodes fire
  when inputs are available.
- **Functional programming** emphasizes immutability and referential
  transparency.
- **Processing-in-memory (PIM)** research addresses the data movement
  problem within the von Neumann paradigm.

Recent work in AI demonstrates the growing relevance of structural
constraints:

- **Geometric Constraints**: Research such as *Manifold-Constrained
  Hyper-Connections* by DeepSeek [\[6\]](#ref-deepseek2025manifold)
  highlights the efficacy of applying geometric inductive biases. This
  supports the SSCCS approach of defining computational processes
  through topological constraints.
- **Structural Parallels**: SSCCS shares conceptual ground with
  State-Space Models (SSMs) like Mamba [\[5\]](#ref-gu2023mamba). While
  these systems achieve high-performance linear recurrences through
  ad-hoc kernel tuning, SSCCS redefines the recurrence not as a
  procedural loop, but as a one-dimensional Scheme of adjacent Segments.
  By shifting from execution-based optimization to the deterministic
  observation of stationary topological constraints, SSCCS offers a
  universal, structure-defined architecture.

These references contextualize SSCCS within the broader intellectual
landscape. In each domain, the shift from execution to observation is
expected to offer advantages that incremental optimization cannot
provide.

## Development Roadmap and milestones

The development roadmap follows a three-phase progression from
Rust-based software emulation to native observation-centric hardware,
utilizing a dual-layer compiler to bridge the transition from existing
von Neumann architectures. This incremental strategy targets empirical
validation across high-performance domains to demonstrate energy
efficiency and deterministic execution through structural observation.
For a detailed execution plan and phased development milestones, please
refer to this appendix for the Roadmap:
\[*<a href="#sec-appendix-roadmap" class="quarto-xref">9</a>*\].

## Conclusion and Future Work

SSCCS establishes five foundational principles:

1.  Computation concerns revelation rather than change.
2.  Structure is more fundamental than process.
3.  Time is a coordinate rather than a flow.
4.  Value is projected rather than intrinsic.
5.  Immutability enables parallelism and verifiability.

The most significant departure is the treatment of time as one
coordinate among many, eliminating global sequentiality and enabling
lock-free concurrency. The compiler’s role correspondingly shifts from
instruction scheduling to topological optimization—mapping logical
adjacency directly onto physical locality.

Open questions remain: formal treatment of nested Field dynamics,
compiler infrastructure for geometric constraints at scale, and
empirical validation of energy efficiency gains across target domains.
Beyond engineering challenges, SSCCS invites a broader reconsideration
of what computing is. If computation can be structured as the revelation
of static potential rather than the execution of mutable instructions,
then many assumptions about hardware design, programming languages, and
system architecture become contingent rather than necessary. The open
.ss format
\[*<a href="#sec-appendix-openformat" class="quarto-xref">13</a>*\] is a
first step toward making these ideas concrete and composable.

SSCCS is not proposed as a universal replacement for all computing. For
problems inherently sequential or interaction-dominant, traditional
models may remain appropriate. But for the growing class of
data-intensive, parallel workloads where the von Neumann bottleneck
dominates, this model offers a fundamentally different trade-off: one
where verifiability, parallelism, and energy efficiency are not features
to be added, but consequences of how computation is defined.

## References

<div id="refs" class="references csl-bib-body" entry-spacing="0">

<div id="ref-horowitz2014computing" class="csl-entry">

<span class="csl-left-margin">\[1\]
</span><span class="csl-right-inline">M. Horowitz, “Computing’s energy
problem (and what we can do about it),” in *2014 IEEE international
solid-state circuits conference (ISSCC)*, IEEE, 2014, pp. 10–14.</span>

</div>

<div id="ref-wulf1995hitting" class="csl-entry">

<span class="csl-left-margin">\[2\]
</span><span class="csl-right-inline">W. A. Wulf and S. A. McKee,
“Hitting the memory wall: Implications of the obvious,” *ACM SIGARCH
Computer Architecture News*, vol. 23, no. 1, pp. 20–24, 1995.</span>

</div>

<div id="ref-borkar2011future" class="csl-entry">

<span class="csl-left-margin">\[3\]
</span><span class="csl-right-inline">S. Borkar and A. A. Chien, “The
future of microprocessors,” *Communications of the ACM*, vol. 54, no. 5,
pp. 67–77, 2011.</span>

</div>

<div id="ref-lucas2014top" class="csl-entry">

<span class="csl-left-margin">\[4\]
</span><span class="csl-right-inline"><span class="nocase">R. Lucas *et
al.*</span>, “Top ten exascale research challenges,” US Department of
Energy, 2014.</span>

</div>

<div id="ref-gu2023mamba" class="csl-entry">

<span class="csl-left-margin">\[5\]
</span><span class="csl-right-inline">A. Gu and T. Dao, “Mamba:
Linear-time sequence modeling with selective state spaces,” *arXiv
preprint arXiv:2312.00752*, 2023, Available:
<https://arxiv.org/abs/2312.00752></span>

</div>

<div id="ref-deepseek2025manifold" class="csl-entry">

<span class="csl-left-margin">\[6\]
</span><span class="csl-right-inline">DeepSeek-AI, “mHC:
Manifold-constrained hyper-connections,” *arXiv preprint
arXiv:2512.24880*, 2025, Available:
<https://arxiv.org/abs/2512.24880></span>

</div>

</div>



## Appendices

## Project Roadmap

SSCCS is designed for incremental adoption—start with software emulation
today, transition to hardware acceleration as the technology matures,
and ultimately deploy on native observation-centric processors. The open
format ensures that investment in specification outlives any particular
implementation.

<div id="fig-roadmap">

``` python
dot("""
digraph Implementation_Roadmap {
    rankdir=LR;
    node [shape=rect];
    Phase1 [label="Phase 1\\nSoftware Emulation\\n(Reference in Rust)"];
    Phase2 [label="Phase 2\\nHardware Acceleration\\n(FPGA / PIM)"];
    Phase3 [label="Phase 3\\nNative Observation-Centric Processors"];
    Phase1 -> Phase2 [label="Validate"];
    Phase2 -> Phase3 [label="Scale"];
    subgraph cluster_goals {
        label="Goals";
        G1 [label="Structural Fidelity"];
        G2 [label="Parallelism"];
        G3 [label="Energy Efficiency"];
    }
    Phase1 -> G1;
    Phase2 -> G2;
    Phase3 -> G3;
}
"""
)
```

Figure 6

</div>

### Implementation Phases

#### Phase 1: Software Emulation (Proof of Concept)

- Rust reference implementation reading the SS format specifications.
- Validate model on small benchmarks.
- Measure determinism, implicit parallelism, data movement reduction.

#### Phase 2: Hardware Acceleration (Transitional)

- Map Schemes to FPGA fabrics.
- Utilize PIM architectures as transitional substrate (UPMEM, Samsung
  FIM).
- Develop compiler targeting CPUs (via SIMD) and FPGA/PIM.
- Begin formal verification.

#### Phase 3: Native Observation-Centric Processors (Long-Term Research)

- Design processor directly instantiating Schemes.
- Integrate memory and logic in unified substrate (e.g., memristor
  arrays).
- Evaluate energy efficiency for target domains.

### Compiler Layer as Migration Bridge

The SSCCS compiler serves a dual purpose:

1.  **Adaptive Embedding (Phase 1-2):** Translate Schemes into von
    Neumann-compatible code (load/store, SIMD) or PIM primitives,
    accepting abstraction overhead.

    *Example:* A climate model grid can be compiled to standard C +
    OpenMP today, while retaining the same format specification for
    future hardware.

2.  **Direct Instantiation (Phase 3):** Map Schemes directly to
    observation-centric hardware primitives, eliminating compatibility
    layers.

    *Example:* The same scheme grid can later be synthesized directly
    onto a memristor array without rewriting.

This dual capability enables gradual migration without requiring a “flag
day” switchover. Organizations can adopt SSCCS incrementally, deploying
on existing infrastructure while preparing for native hardware.

### Domain Validations

SSCCS is intended for validation across multiple domains.

| Domain | Traditional Challenge | Expected Advantages |
|----|----|----|
| Climate modelling | Massive state space, grid data movement | Constraint isolation, minimal data transfer |
| Space systems | Radiation-induced errors, power constraints | Structural reproducibility, verifiable execution |
| Protein folding | Combinatorial explosion, long time scales | Massive parallel observation |
| Swarm robotics | Coordination overhead, limited communication | Recursive composition, emergent coordination |
| Financial modelling | Real-time constraints, complex dependencies | Deterministic projections, no race conditions |
| Cryptographic systems | Side-channel attacks, verification complexity | Immutable structure enables formal verification |
| Autonomous vehicles | Sensor fusion, real-time decision making | Constraint-based observation, deterministic response |

## Vector Addition Example

Consider the addition of two vectors of length $N$.

### Traditional Approach

In a traditional architecture, a loop iterates over indices, loading
each element from memory into registers, performing the addition, and
storing the result back.

``` rust
fn add_vectors(a: &[f64], b: &[f64]) -> Vec<f64> {
    assert_eq!(a.len(), b.len());
    let mut result = Vec::with_capacity(a.len());
    for i in 0..a.len() {
        result.push(a[i] + b[i]); // loads a[i], b[i]; stores result[i]
    }
    result
}
```

- **Data Movement**: $2N$ loads + $N$ stores = $3N$ total memory
  transfers.
- **Sequential Dependency**: Loop-carried dependencies limit
  parallelisation.
- **Cache Behaviour**: Performance is highly dependent on memory layout;
  random access or misalignment causes cache misses.

### SSCCS Approach

A Scheme defines a set of Segments representing the vectors. The
compiler lays out the Segments consecutively in memory. An observation
of the entire structure yields a projection that is the sum vector.

``` rust
let a = Segment::vector(0..N, initial_values);
let b = Segment::vector(0..N, initial_values);
let scheme = Scheme::add_vectors(a, b);
let field = Field::new();
let sum = observe(scheme, field);
```

- **Data Movement**: Zero input movement. Segments remain stationary
  (“Logic-at-Rest”). Only the resulting projection (a single vector of
  length $N$) is transmitted.
- **Parallelism**: Structural independence allows all element pairs to
  be observed concurrently without explicit synchronisation or
  partitioning.
- **Locality**: Enforced by the compiler’s topological mapping, treating
  memory as an active topology rather than passive storage.

#### Comparison Table

| Aspect | Traditional (Procedural) | SSCCS (Structural) |
|----|----|----|
| Input Data Movement | $2N$ loads | Zero (Stationary Segments) |
| Output Data Movement | $N$ stores | $N$ (Projection) |
| Concurrency | Requires explicit parallelisation | Implicit (Structural independence) |
| Synchronisation | Locks/atomics for shared state | None (Immutability guaranteed) |
| Memory Role | Passive storage | Active topology |
| Auditability | Requires external tracing | Intrinsic to Specification |

## Scaling to N-Dimensional Tensors and Graphs

The structural principles of SSCCS extend beyond linear vectors to
higher-dimensional and non-linear data structures.

### N-Dimensional Tensors

In SSCCS, an $N$-dimensional tensor is represented as a set of Segments
where adjacency relations are defined across multiple axes within the
Scheme.

<div id="fig-scaling-tensor">

``` python
dot("""
digraph TensorReshaping {
    graph [nodesep=0.5, ranksep=0.6, ratio=shrink, center=true];
    node [fontsize=10];

    subgraph cluster_tensor {
        rankdir=TB;
        label="Tensor (2D Matrix)";
        style=dashed; color=gray;

        // Original grid
        node [shape=box, width=0.4, height=0.4, fixedsize=true];
        { rank=same; a11 [label="a11", xlabel="(0,0)"]; a12 [label="a12", xlabel="(0,1)"]; }
        { rank=same; a21 [label="a21", xlabel="(1,0)"]; a22 [label="a22", xlabel="(1,1)"]; }

        // Field reorientation node
        reshape [shape=plaintext, label="Field reorients\nobservation path", fontsize=9];

        // Edges to reshape
        edge [style=dashed, arrowhead=vee, color=gray50, constraint=false];
        a11 -> reshape; a12 -> reshape; a21 -> reshape; a22 -> reshape;

        // Transposed grid
        node [shape=box, width=0.4, height=0.4];
        { rank=same; t11 [label="a11", xlabel="(0,0)"]; t12 [label="a21", xlabel="(0,1)"]; }
        { rank=same; t21 [label="a12", xlabel="(1,0)"]; t22 [label="a22", xlabel="(1,1)"]; }

        // Edges from reshape to transposed
        edge [style=dashed, arrowhead=vee, color=gray50, constraint=false];
        reshape -> t11; reshape -> t12; reshape -> t21; reshape -> t22;

        // Invisible edges for vertical alignment
        edge [style=invis];
        a21 -> reshape -> t11;
    }
}
"""
)
```

Figure 7

</div>

- **Zero-Copy Reshaping**: Traditional systems require physical data
  movement ($O(N)$ or $O(N^2)$) to perform operations like transposition
  or reshaping. In SSCCS, reshaping is a metadata-only operation. By
  reorienting the Field’s observation path over stationary Segments, the
  dimensionality of the Projection changes without moving a single bit
  in memory ($O(1)$).
- **Logical Adjacency**: For operations like matrix multiplication, the
  compiler maps Segments to ensure that the required operands for a
  specific Field are physically co-located. This transforms what would
  be complex indexing logic in a CPU into a direct physical property of
  the memory topology.

## Complex Graph Processing

Graph algorithms (e.g., PageRank, GNNs) are traditionally bottlenecked
by “Pointer Chasing,” which causes severe cache thrashing and memory
latency.

<div id="fig-scaling-graph">

``` python
dot("""
digraph Graph_Cluster_Detailed {
    graph [
        fontsize = 12,
        nodesep = 0.6,
        ranksep = 0.7,
        size = "8,5!",
        ratio = shrink,
        center = true,
    ];

    // --- Graph nodes (Segments) ---
    node [shape = circle, width = 0.6, height = 0.6, fixedsize = true, style = solid, color = black, fontsize = 10];
    { rank = same; n1; n2; n3; n4; n5; }

    n1 [label = "A"];
    n2 [label = "B"];
    n3 [label = "C"];
    n4 [label = "D"];
    n5 [label = "E"];

    // Structural edges (solid, black)
    edge [arrowhead = none, style = solid, color = black, penwidth = 1.2];
    n1 -> n2;
    n1 -> n3;
    n2 -> n4;
    n3 -> n4;
    n4 -> n5;

    // Optional long‑range connections (dashed, gray)
    edge [arrowhead = none, style = dashed, color = gray, penwidth = 1];
    n2 -> n5;
    n3 -> n5;

    // --- Field node (influence) ---
    node [shape = plaintext, fontsize = 10, width = 1.5, height = 0.4];
    field [label = "Field F\n(propagates across graph)", margin = 0.2];

    // Field influences all nodes (dashed arrows)
    edge [arrowhead = vee, style = dashed, color = gray, constraint = false];
    field -> n1;
    field -> n2;
    field -> n3;
    field -> n4;
    field -> n5;

    // --- Projection states (below) ---
    node [shape = box, width = 0.8, height = 0.3, fixedsize = false, fontsize = 9, style = solid, color = black];
    { rank = same; p1; p2; p3; p4; p5; }

    p1 [label = "state A'"];
    p2 [label = "state B'"];
    p3 [label = "state C'"];
    p4 [label = "state D'"];
    p5 [label = "state E'"];

    // Observation edges (solid arrows)
    edge [arrowhead = normal, style = solid, color = black, constraint = true];
    n1 -> p1;
    n2 -> p2;
    n3 -> p3;
    n4 -> p4;
    n5 -> p5;

    // --- Explanatory notes ---
    node [shape = plaintext, fontsize = 8, fontcolor = black, margin = 0.1];
    
}
"""
)
```

Figure 8

</div>

- **Segment-as-Node**: Each node and its properties are encapsulated in
  a Segment.
- **Adjacency-as-Structure**: Edges are defined as structural
  constraints within the Scheme, not as memory pointers to be followed
  sequentially.
- **Field-based Traversal**: A Field propagates across the entire Scheme
  in a single observation cycle. Instead of “visiting” nodes, the
  observer captures the emergent state of the entire graph
  simultaneously.
- **Concurrency**: This eliminates vertex-centric synchronization
  (locks/mutexes). All nodes update their state in parallel as a
  deterministic consequence of the Field’s interaction with the Scheme’s
  topology.

### Comparison: Computational Density at Scale

| Computational Task | Traditional Bottleneck | SSCCS Solution |
|----|----|----|
| Tensor Reshaping | Physical data reshuffling ($O(N^d)$) | Metadata-level Field reorientation ($O(1)$) |
| Matrix Contraction | Memory bandwidth & indexing overhead | Hardwired adjacency in the Scheme |
| Graph Traversal | High latency due to random access | Distributed parallel observation |
| Sparse Operations | Complex indexing & storage overhead | Non-linear Scheme mapping (skipping null-space) |

The scaling of SSCCS addresses the Curse of Dimensionality by decoupling
the logical structure of data from the physical cost of its traversal.
While traditional architectures expend energy moving data to accommodate
logic, SSCCS modifies the Field to accommodate the stationary structure.

## Open Format Specification (Draft)

The `.ss` format is a declarative language for specifying the
**topological structure** of an SSCCS computation. It describes the
geometric and relational properties of a computational space, leaving
all physical mapping decisions to the hardware‑specific compiler
backend. The format captures *what* the structure is; not *how* to
execute it.

### Core Components

The following diagram illustrates how the four core components of a
`.ss` description relate to each other. Notice that no memory layout or
instruction flow appears – only the static topology of the computation.

<div id="fig-ss-format-topology">

``` python
dot("""
digraph SSFormat_Topology {
    rankdir=LR;
    nodesep=0.8;
    ranksep=1.0;
    graph [fontsize=11, pad=0.5];
    node [fontsize=10];
    edge [fontsize=9];
    
    subgraph cluster_axes {
        label = "Axes (Dimensional Space)";
        labelloc=t;
        style=dashed;
        color=gray;
        fontsize=10;
        
        node [shape=point, width=0.3, height=0.3, fillcolor=black, style=filled];
        ax1 [xlabel="x: 0..N"];
        ax2 [xlabel="y: 0..N"];
        ax3 [xlabel="z: 0..N (optional)"];
        
        { rank=same; ax1; ax2; ax3; }
    }
    
    subgraph cluster_segments {
        label = "Segments (Coordinate Atoms)";
        labelloc=t;
        style=dashed;
        color=gray;
        fontsize=10;
        
        node [shape=circle, width=0.5, height=0.5, style=filled, fillcolor=white, color=black];
        s1 [label="S₁\\n(0,0)"];
        s2 [label="S₂\\n(1,0)"];
        s3 [label="S₃\\n(0,1)"];
        s4 [label="S₄\\n(1,1)"];
        
        { rank=same; s1; s2; s3; s4; }
    }
    
    subgraph cluster_relations {
        label = "Relations (Topological Fabric)";
        labelloc=t;
        style=dashed;
        color=gray;
        fontsize=10;
        
        node [shape=diamond, width=0.8, height=0.6, style=filled, fillcolor=white, color=black];
        r1 [label="Adjacency\n(4-connected, ...)"];
        r2 [label="Metric Space\n(Manhattan, ...)"];
        r3 [label="Boundary\n(Periodic, Fixed)"];
        
        { rank=same; r1; r2; r3; }
    }
    
    subgraph cluster_observation {
        label = "Observation (State Projection)";
        labelloc=t;
        style=dashed;
        color=gray;
        fontsize=10;
        
        node [shape=ellipse, width=1.4, height=0.8, style=filled, fillcolor=white, color=black];
        obs [label="Ω (Field + Scheme)\nTrigger | Resolution | Format"];
    }
    
    subgraph cluster_projection {
        label = "Projection (Result)";
        labelloc=t;
        style=dashed;
        color=gray;
        fontsize=10;
        
        node [shape=box, width=1.2, height=0.6, style=filled, fillcolor=white, color=black];
        proj [label="P = Ω(Σ, F)"];
    }
    
    edge [arrowhead=normal, style=solid, color=black, penwidth=1.2];
    
    ax1 -> s1 [style=dashed, color=gray, penwidth=0.8, arrowhead=none];
    ax1 -> s2 [style=dashed, color=gray, penwidth=0.8, arrowhead=none];
    ax2 -> s3 [style=dashed, color=gray, penwidth=0.8, arrowhead=none];
    ax2 -> s4 [style=dashed, color=gray, penwidth=0.8, arrowhead=none];
    
    s1 -> r1 [style=solid, color=black, penwidth=1.0];
    s2 -> r1 [style=solid, color=black, penwidth=1.0];
    s3 -> r1 [style=solid, color=black, penwidth=1.0];
    s4 -> r1 [style=solid, color=black, penwidth=1.0];
    
    r1 -> obs [style=solid, color=black, penwidth=1.2];
    r2 -> obs [style=solid, color=black, penwidth=1.2];
    r3 -> obs [style=solid, color=black, penwidth=1.2];
    
    obs -> proj [style=solid, color=black, penwidth=1.5, label="P"];
    
    node [shape=plaintext, fontsize=9, fontcolor=gray];
    hw_note [label="Physical mapping deferred to hardware backend"];
    
    edge [style=dashed, color=gray, penwidth=0.5, arrowhead=none];
    proj -> hw_note;
}
""")
```

Figure 9

</div>

### Component Details

#### Axes

Define the coordinate space: names, ranges (discrete or continuous), and
optional manifold properties (e.g., toroidal, bounded). They establish
the dimensional foundation upon which Segments are placed.

#### Segments

Atomic coordinate points. Each Segment is identified by its coordinates
$(x, y, z, \dots)$ and a cryptographic hash derived from them. Segments
are immutable and stateless – they carry no values, only position.

#### Relations

Relations replace traditional control flow (loops, conditionals) with a
static description of connectivity and proximity. The topological fabric
that connects Segments. This block encodes:

- **Adjacency**: How Segments are connected (e.g., 4‑connected,
  8‑connected, arbitrary graph).
- **Metric Space**: The distance function $d(s_i, s_j)$ that governs
  interaction strength (e.g., Manhattan, Euclidean, graph distance).
- **Boundary Conditions**: The shape of the manifold (e.g., `Periodic`
  for a torus, `Fixed` for a finite grid).

#### Observation

Defines how a Field’s dynamic constraints interact with the static
Scheme to produce a Projection. It includes:

- **Trigger**: The condition that initiates observation (e.g.,
  `Equilibrium`, `ExternalPulse`, `Timer`).
- **Resolution Strategy**: How multi‑segment interactions are resolved
  into a single output (e.g., summation, maximum, tensor contraction).
- **Projection Format**: The mathematical type of the result (e.g.,
  scalar, vector, tensor).

### Key characteristics

1.  **Non‑linear addressing** – Segments are identified by coordinate
    tuples, not memory offsets.
2.  **Relation‑defined computation** – What traditional code expresses
    as loops and conditionals is encoded in the connectivity and metric
    of the `Relations` block.
3.  **Observation as collapse** – The `Observation` block specifies how
    a Field’s constraints resolve the Scheme’s potential into a
    deterministic Projection.
4.  **Deferred physical mapping** – No memory layout or instruction
    sequence is included; the compiler backend maps the topology to
    concrete hardware (SRAM, DRAM, HBM, etc.) based solely on the
    declared relations.

### Cryptographic Identity

A Schema’s identity is derived solely from its topological properties.
Changing a physical implementation detail (e.g., cache‑line alignment)
does **not** affect the `SchemeId`. However, altering the connectivity
or the metric space produces a new, distinct identity:

$$SchemeId = H(\text{Axes} + \text{Segments} + \text{Relations} + \text{ObservationRules})$$
