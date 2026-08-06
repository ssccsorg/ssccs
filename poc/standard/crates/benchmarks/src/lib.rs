//! Validation-only benchmarking kernels for the reference simulation.
//!
//! Three kernels, each implemented twice: a pure Rust baseline (the von
//! Neumann execution of the same computation) and an SSCCS formulation as
//! Scheme plus Field plus Projector observed through `ssccs_core::observe`.
//! The measured overhead is the cost of the reference simulation on
//! existing hardware. It is validation evidence for the practical plane;
//! it never shapes the model.
//!
//! Kernel selection follows the diagnosis: vector addition (memory-bound),
//! 2D convolution (compute-bound), and graph BFS (irregular).

use ssccs_core::{Constraint, Coordinates, Field, Projector, Segment, observe};
use std::collections::{HashSet, VecDeque};

// ═══════════════════════════════════════════════════════════════════════
// Kernel 1: vector addition (memory-bound)
// ═══════════════════════════════════════════════════════════════════════

/// Baseline: element-wise addition of two vectors.
pub fn vec_add_baseline(a: &[i64], b: &[i64]) -> Vec<i64> {
    a.iter().zip(b).map(|(x, y)| x + y).collect()
}

/// Projector for the vector addition scheme: sums the two coordinates of a
/// segment, which carries `[a_i, b_i]`.
#[derive(Debug)]
pub struct PairSumProjector;

impl Projector for PairSumProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        Some(segment.coordinates().get_axis(0)? + segment.coordinates().get_axis(1)?)
    }
}

/// Builds the vector addition scheme: one segment `[a_i, b_i]` per index.
pub fn build_vec_add_scheme(a: &[i64], b: &[i64]) -> Vec<Segment> {
    a.iter()
        .zip(b)
        .map(|(x, y)| Segment::from_values(vec![*x, *y]))
        .collect()
}

/// SSCCS path: observe every segment with an allow-all field, collecting
/// the pair-sum projections in segment order.
pub fn vec_add_ssccs(
    segments: &[Segment],
    field: &Field,
    projector: &PairSumProjector,
) -> Vec<i64> {
    segments
        .iter()
        .map(|s| observe(field, s, projector).expect("allow-all field"))
        .collect()
}

// ═══════════════════════════════════════════════════════════════════════
// Kernel 2: 2D convolution (compute-bound)
// ═══════════════════════════════════════════════════════════════════════

/// Baseline: 3x3 convolution over an MxN grid.
pub fn conv2d_baseline(input: &[i64], width: usize, height: usize, kernel: &[i64; 9]) -> Vec<i64> {
    assert_eq!(input.len(), width * height);
    let mut out = vec![0i64; width * height];
    for y in 1..height - 1 {
        for x in 1..width - 1 {
            let mut acc = 0i64;
            for ky in 0..3usize {
                for kx in 0..3usize {
                    let i = (y + ky - 1) * width + (x + kx - 1);
                    acc += input[i] * kernel[ky * 3 + kx];
                }
            }
            out[y * width + x] = acc;
        }
    }
    out
}

/// Projector for the convolution scheme: a segment carries `[x, y, p00,
/// p01, p02, p10, p11, p12, p20, p21, p22]`, the 3x3 patch around the
/// output position. The kernel weights are baked in.
#[derive(Debug)]
pub struct PatchConvProjector {
    /// 3x3 kernel weights.
    pub kernel: [i64; 9],
}

impl Projector for PatchConvProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let coords = segment.coordinates();
        let mut acc = 0i64;
        for (k, weight) in self.kernel.iter().enumerate() {
            acc = acc.checked_add(coords.get_axis(2 + k)? * weight)?;
        }
        Some(acc)
    }
}

/// Builds the convolution scheme: one segment per output pixel, whose
/// coordinates are the position followed by the 3x3 input patch.
pub fn build_conv_scheme(input: &[i64], width: usize, height: usize) -> Vec<Segment> {
    assert_eq!(input.len(), width * height);
    let mut segments = Vec::with_capacity((width - 2) * (height - 2));
    for y in 1..height - 1 {
        for x in 1..width - 1 {
            let mut coords = vec![x as i64, y as i64];
            for ky in 0..3usize {
                for kx in 0..3usize {
                    coords.push(input[(y + ky - 1) * width + (x + kx - 1)]);
                }
            }
            segments.push(Segment::from_values(coords));
        }
    }
    segments
}

/// SSCCS path: observe every patch segment, collapsing the patch with the
/// baked kernel weights.
pub fn conv2d_ssccs(
    segments: &[Segment],
    field: &Field,
    projector: &PatchConvProjector,
) -> Vec<i64> {
    segments
        .iter()
        .map(|s| observe(field, s, projector).expect("allow-all field"))
        .collect()
}

// ═══════════════════════════════════════════════════════════════════════
// Kernel 3: graph BFS (irregular)
// ═══════════════════════════════════════════════════════════════════════

/// Deterministic undirected graph: a ring plus chords of stride 5, so
/// every node is reachable from node 0.
pub fn build_ring_chord_graph(n: usize) -> Vec<Vec<usize>> {
    let mut adj = vec![Vec::new(); n];
    for i in 0..n {
        for d in [1usize, 5] {
            let j = (i + d) % n;
            adj[i].push(j);
            adj[j].push(i);
        }
    }
    for list in &mut adj {
        list.sort_unstable();
        list.dedup();
    }
    adj
}

/// Baseline: FIFO BFS from node 0, returning the visit order.
pub fn bfs_baseline(adj: &[Vec<usize>], start: usize) -> Vec<usize> {
    let mut visited = vec![false; adj.len()];
    let mut order = Vec::with_capacity(adj.len());
    let mut queue = VecDeque::new();
    visited[start] = true;
    queue.push_back(start);
    while let Some(node) = queue.pop_front() {
        order.push(node);
        for &next in &adj[node] {
            if !visited[next] {
                visited[next] = true;
                queue.push_back(next);
            }
        }
    }
    order
}

/// Projector for the BFS scheme: identity on the node coordinate, with
/// adjacency semantics in `possible_next_coordinates`.
#[derive(Debug)]
pub struct GraphAdjProjector {
    /// Baked adjacency: node index to neighbor indices.
    pub adj: Vec<Vec<usize>>,
}

impl Projector for GraphAdjProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        segment.coordinates().get_axis(0)
    }

    fn possible_next_coordinates(&self, coords: &Coordinates) -> Vec<Coordinates> {
        let node = coords.get_axis(0).unwrap_or(0) as usize;
        self.adj
            .get(node)
            .map(|neighbors| {
                neighbors
                    .iter()
                    .map(|&n| Coordinates::new(vec![n as i64]))
                    .collect()
            })
            .unwrap_or_default()
    }
}

/// Constraint for the BFS scheme: allows only the current frontier.
#[derive(Debug)]
pub struct FrontierConstraint {
    frontier: HashSet<i64>,
}

impl FrontierConstraint {
    pub fn new(frontier: &[i64]) -> Self {
        Self {
            frontier: frontier.iter().copied().collect(),
        }
    }
}

impl Constraint for FrontierConstraint {
    fn allows(&self, coords: &Coordinates) -> bool {
        coords
            .get_axis(0)
            .map(|v| self.frontier.contains(&v))
            .unwrap_or(false)
    }

    fn describe(&self) -> String {
        format!("node in frontier of {} members", self.frontier.len())
    }
}

/// Builds the BFS scheme: one single-coordinate segment per node.
pub fn build_bfs_scheme(n: usize) -> Vec<Segment> {
    (0..n as i64)
        .map(|i| Segment::from_values(vec![i]))
        .collect()
}

/// SSCCS path: level-iterated observation. The Scheme is the graph
/// structure, the Field is the evolving frontier constraint (the mutable
/// layer), the Projector carries adjacency semantics, and each observation
/// collapses the current level. Returns the visit order.
pub fn bfs_ssccs(segments: &[Segment], projector: &GraphAdjProjector, start: usize) -> Vec<i64> {
    let mut visited = HashSet::new();
    let mut order = Vec::with_capacity(segments.len());
    let mut frontier = vec![start as i64];
    while !frontier.is_empty() {
        let mut field = Field::new();
        field.add_constraint(FrontierConstraint::new(&frontier));
        let mut next = HashSet::new();
        for segment in segments {
            if let Some(node) = observe(&field, segment, projector) {
                visited.insert(node);
                order.push(node);
                let coords = Coordinates::new(vec![node]);
                for neighbor in projector.possible_next_coordinates(&coords) {
                    let nv = neighbor.get_axis(0).expect("neighbor coordinate");
                    if !visited.contains(&nv) {
                        next.insert(nv);
                    }
                }
            }
        }
        frontier = next.into_iter().collect();
    }
    order
}
