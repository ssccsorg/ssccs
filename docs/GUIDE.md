# Core Concepts Guide
SSCCS Foundation

## What is SSCCS?

SSCCS (Schema–Segment Composition Computing System) is a new way of
thinking about computation. Instead of moving data around and executing
instructions step by step (the von Neumann model), SSCCS treats
computation as **the observation of fixed structure under changing
conditions**.

Think of it like a sculpture that never moves. You can shine light on it
from different angles, and each time you get a different shadow. The
sculpture stays the same, but what you see changes. In SSCCS, the
sculpture is your data structure, the light is your problem, and the
shadow is your answer.

## A Deeper Analogy: Maps and Satellite Imagery

Imagine you have a map. The map itself is fixed—it has coordinates,
roads, and boundaries. Now imagine a satellite taking pictures of the
same area under different conditions: summer, winter, morning, night,
with different filters.

| SSCCS Concept | Map Analogy |
|----|----|
| **Segment** | A single coordinate point on the map (e.g., latitude, longitude). It has no information—just a location. |
| **Scheme** | The map itself. It defines the coordinate system, scale, and how points are connected (roads, borders). |
| **Field** | The observation conditions: season, time of day, weather, camera filter. These change dynamically. |
| **Observation** | The moment the satellite takes a picture. It combines the fixed map with current conditions. |
| **Projection** | The resulting image. It reveals what the map looks like under those specific conditions. |

The map never changes. The coordinates never move. But each observation
produces a different image—a different “value” from the same underlying
structure.

## The Five Core Ideas

| Concept | What it is | What it does |
|----|----|----|
| **Segment** | An immutable point in space. It has coordinates and a unique ID, but stores no value. It just exists. | Serves as the atomic unit of potential. Segments are stateless and never change. |
| **Scheme** | A blueprint for structure. Defines how Segments are arranged—their geometry, adjacency, and layout. | Encodes the “shape” of computation: axes, connectivity, memory layout, and observation rules. |
| **Field** | A set of dynamic rules. Imposes conditions on the Scheme, like “add these two Segments” or “find the maximum”. | The only mutable layer. It holds constraints that determine which configurations are possible. |
| **Observation** | The only active event. Combines Scheme and Field to produce a result. | Collapses the structure’s potential into a deterministic projection. No data moves during observation. |
| **Projection** | The result. A transient value that emerges from Observation. It’s not stored—if you need it again, you observe again. | What we traditionally call “output” or “data”. It is revealed, not computed step by step. |

## Segment in Depth

A Segment is the most fundamental building block. It is **a pure
coordinate point with no stored value**. Think of it as a location on a
map: the point itself contains no information, but its position exists.

**Properties:** - **Immutable**: Once created, a Segment never
changes. - **Stateless**: It holds no value—only coordinates and a
cryptographic hash ID. - **Identifiable**: Each Segment has a unique ID
derived from its coordinates.

Segments carry **potential**. The actual “value” is revealed later
through Observation. For example, in a 2D array, each cell is a Segment.
The cell’s value isn’t stored in the Segment; it emerges from the Scheme
and Field interaction.

**Common Misconceptions:**

| Misconception | Truth |
|----|----|
| Segments store values. | No, they only hold coordinates and identity. Values are revealed via observation. |
| Segments are like variables. | Variables are mutable; Segments are immutable. They are more like fixed coordinates. |
| Many Segments consume lots of memory. | Segments themselves are lightweight metadata; they can be more efficient than traditional data structures. |
| Segments are hardware memory cells. | Conceptually similar, but Segments are logical units that can map to multiple physical memory cells. |

## The Simplest Example: 1 + 1 = 2

Let’s see how SSCCS handles the most basic operation: adding two
numbers.

``` rust
// 1. Define a Scheme with two Segments
//    Segment A at coordinate (0), Segment B at coordinate (1)
let scheme = Scheme::line(length: 2);

// 2. Set up a Field that says "add the values"
//    But wait—Segments have no values yet!
let field = Field::new().with_operation("add");

// 3. Before observing, we need to put numbers into the system.
//    In SSCCS, we don't "assign" values to Segments.
//    Instead, we set up a Field that gives them meaning.
//    Let's create a special Field that says:
//    "Segment at (0) represents 1, Segment at (1) represents 1"
let input_field = Field::new()
    .with_value_at(0, 1)
    .with_value_at(1, 1);

// 4. Now observe: combine the structure with both Fields
let combined_field = input_field.merge_with(add_field);
let projection = observe(scheme, combined_field);
// projection = 2
```

**What happened?** - The Scheme provided the structure: two points in a
line. - The first Field gave those points meaning: “point 0 is 1, point
1 is 1”. - The second Field provided the operation: “add what you
find”. - Observation combined everything and revealed the result: 2.

**Key insight:** The numbers 1 and 1 were never “stored” in the
Segments. They were attached as constraints in the Field. The Segments
themselves remained empty—pure coordinates. The addition happened as a
collapse of structure under constraints, not as a sequence of
instructions.

## What Does a Developer Do?

In traditional programming, you write instructions. In SSCCS, you
**design structure** and **set conditions**.

1.  **Define a Scheme**:
    - Choose your data shape: vector, matrix, graph, etc.  
    - Specify axes, adjacency (e.g., 4‑neighbor grid), and memory layout
      (row‑major, column‑major, etc.).  
    - Define observation rules (e.g., “when observed, sum all
      Segments”).
2.  **Place Segments**:
    - Segments are automatically generated from the Scheme.  
    - Each Segment gets coordinates and an ID—no initial values.
3.  **Set up a Field**:
    - Add dynamic constraints: “add corresponding elements”, “find
      maximum”, “apply a transformation”.  
    - Fields can be changed at runtime.
4.  **Observe**:
    - Call `observe(scheme, field)`.  
    - The system evaluates the Scheme under the Field’s rules and
      returns a Projection.  
    - That’s your answer.
5.  **The Compiler’s Role**:
    - The compiler analyzes the Scheme and maps it to physical memory.  
    - It ensures that logically adjacent Segments become physically
      adjacent in hardware (cache lines, memory banks).  
    - This eliminates most data movement—only results travel.

**Overall Flow:**

    Developer: Define Scheme + (implicitly) Segments + initial Field
            ↓
    Compiler: Structural mapping → physical memory layout
            ↓
    Runtime: Field may be updated
            ↓
    Observation: observe(scheme, field) → Projection (result)

**Future Layer: Translation Compiler**

The flow described so far assumes that developers design Schemas and
place Segments manually. In reality, however, vast amounts of existing
data (CSV, JSON, databases, log files, etc.) are already present. How
can this data be brought into the SSCCS structure?

This is where the Translation Compiler comes in.

- **Mission**: Analyze data formats, extract dimensions, types, and
  relationships → generate Scheme (`.ss`) files → automatically place
  Segments.
- **Status**: Not yet developed. This layer is planned for a separate
  phase after the core foundation is stabilized. For now, developers
  design structures manually.

## Concrete Examples

## Example 1: Adding Two Vectors

``` rust
// 1. Scheme: two vectors side by side
let scheme = Scheme::vectors(2, length: 1024);

// 2. Segments exist automatically (no explicit creation)

// 3. Field: "add corresponding elements"
let field = Field::new().with_operation("add");

// 4. Observe: get the result vector
let sum_vector = observe(scheme, field);
```

No loops, no explicit parallelism, no data movement—the structure does
the work.

## Example 2: Sum of a 2D Grid

``` rust
// 1. Scheme: a 3x3 grid with row-major layout
let scheme = Scheme::grid_2d(rows: 3, cols: 3, layout: RowMajor);

// 2. Segments automatically placed at (0,0)..(2,2)

// 3. Field: "sum all values"
let field = Field::new().with_constraint("sum_all");

// 4. Observe: get the total sum (a scalar)
let total = observe(scheme, field);
```

Again, the programmer only describes the structure and the constraint;
the computation emerges.

## Example 3: The Ultimate Simple Case — 1 + 1 = 2

``` rust
// Step 1: A Scheme with just two points in a line
let scheme = Scheme::line(2);

// Step 2: A Field that gives meaning to those points
let field = Field::new()
    .bind_value(0, 1)      // "the point at coordinate 0 is 1"
    .bind_value(1, 1)      // "the point at coordinate 1 is 1"
    .with_operation("add"); // "and then add them"

// Step 3: Observe
let result = observe(scheme, field); // result = 2
```

## Why This Matters

- **Energy Efficiency**: Data movement consumes 60–80% of energy in
  modern systems. SSCCS keeps data stationary—only results move.
- **Implicit Parallelism**: Immutable Segments can be observed
  concurrently without locks or race conditions.
- **Intrinsic Verifiability**: Every observation is deterministic and
  traceable from blueprint to result. Security follows from geometry,
  not added checks.

## In a Nutshell: How to Explain SSCCS

> “In SSCCS, a developer doesn’t write instructions that manipulate
> data. Instead, they design a fixed structure (Scheme) and define
> dynamic conditions (Field). Computation happens when you observe the
> structure under those conditions—like taking a satellite photo of a
> map. The map never changes, but each photo reveals different
> information. Even something as simple as 1+1=2 works this way: the
> numbers aren’t stored in memory cells; they’re attached as
> constraints, and the addition emerges from observing the structure.
> This shift from ‘doing’ to ‘revealing’ eliminates data movement, makes
> parallelism automatic, and makes every result inherently auditable.”

------------------------------------------------------------------------

© 2026 [SSCCS Foundation](https://ssccs.org) — A non-profit research and
engineering initiative building a computing model and compiler
infrastructure.

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
