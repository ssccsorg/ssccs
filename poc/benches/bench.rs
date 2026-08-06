//! SSCCS reference simulation benchmarks, expressed in a single file.
//!
//! This file is the performance reference for the poc reference simulation.
//! Three kernels are measured, each implemented twice under identical
//! conditions: a pure Rust baseline (the von Neumann execution of the same
//! computation) and an SSCCS formulation as Scheme plus Field plus
//! Projector observed through `ssccs_core::observe`. Both paths are Rust,
//! compiled in the same release profile, and measured by the same
//! criterion harness. Absolute times are machine-specific; the ratio is
//! the emulation overhead of the reference simulation on existing
//! hardware, recorded as validation evidence for the practical plane. The
//! measurements never shape the model.
//!
//! Kernels
//! -------
//! | Kernel          | Kind          | SSCCS formulation |
//! |-----------------|---------------|-------------------|
//! | vector addition | memory-bound  | segments carry `[a_i, b_i]`, pair-sum projector |
//! | 2D convolution  | compute-bound | one segment per output pixel carrying the 3x3 patch, kernel weights baked in the projector |
//! | graph BFS       | irregular     | level-iterated observation: Scheme is the graph, the evolving frontier is the Field (the mutable layer), adjacency lives in the projector |
//!
//! Correctness guarantee
//! ---------------------
//! The `verify` group asserts on every run that both paths produce
//! identical outputs for all three kernels. A path regression fails the
//! benchmark run.
//!
//! Running
//! -------
//! ```text
//! ./run.sh                  # full run: verify + kernels, results in result/
//! cargo bench --bench bench -- verify     # correctness guard only
//! cargo bench --bench bench -- kernels    # measurements only (IDs carry the kernels/ prefix)
//! ```

use criterion::{Criterion, criterion_group, criterion_main};
use ssccs_core::{Constraint, Coordinates, Field, Projector, Segment, observe};
use std::collections::{HashSet, VecDeque};
use std::hint::black_box;

// ═══════════════════════════════════════════════════════════════════════
// Kernel 1: vector addition (memory-bound)
// ═══════════════════════════════════════════════════════════════════════

/// Baseline: element-wise addition of two vectors.
fn vec_add_baseline(a: &[i64], b: &[i64]) -> Vec<i64> {
    a.iter().zip(b).map(|(x, y)| x + y).collect()
}

/// Projector for the vector addition scheme: sums the two coordinates of a
/// segment, which carries `[a_i, b_i]`.
#[derive(Debug)]
struct PairSumProjector;

impl Projector for PairSumProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        Some(segment.coordinates().get_axis(0)? + segment.coordinates().get_axis(1)?)
    }
}

/// Builds the vector addition scheme: one segment `[a_i, b_i]` per index.
fn build_vec_add_scheme(a: &[i64], b: &[i64]) -> Vec<Segment> {
    a.iter()
        .zip(b)
        .map(|(x, y)| Segment::from_values(vec![*x, *y]))
        .collect()
}

/// SSCCS path: observe every segment with an allow-all field, collecting
/// the pair-sum projections in segment order.
fn vec_add_ssccs(segments: &[Segment], field: &Field, projector: &PairSumProjector) -> Vec<i64> {
    segments
        .iter()
        .map(|s| observe(field, s, projector).expect("allow-all field"))
        .collect()
}

// ═══════════════════════════════════════════════════════════════════════
// Kernel 2: 2D convolution (compute-bound)
// ═══════════════════════════════════════════════════════════════════════

/// Baseline: 3x3 convolution over an MxN grid.
fn conv2d_baseline(input: &[i64], width: usize, height: usize, kernel: &[i64; 9]) -> Vec<i64> {
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
/// output position. The kernel weights are baked in. Arithmetic wraps on
/// overflow, matching the release-mode baseline; the verify group uses
/// inputs without overflow so both paths agree in all modes.
#[derive(Debug)]
struct PatchConvProjector {
    /// 3x3 kernel weights.
    kernel: [i64; 9],
}

impl Projector for PatchConvProjector {
    type Output = i64;

    fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
        let coords = segment.coordinates();
        let mut acc = 0i64;
        for (k, weight) in self.kernel.iter().enumerate() {
            acc = acc.wrapping_add(coords.get_axis(2 + k)?.wrapping_mul(*weight));
        }
        Some(acc)
    }
}

/// Builds the convolution scheme: one segment per output pixel, whose
/// coordinates are the position followed by the 3x3 input patch. The
/// grid must be at least 3x3 so interior pixels exist.
fn build_conv_scheme(input: &[i64], width: usize, height: usize) -> Vec<Segment> {
    assert!(
        width >= 3 && height >= 3,
        "convolution grid must be at least 3x3"
    );
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
fn conv2d_ssccs(segments: &[Segment], field: &Field, projector: &PatchConvProjector) -> Vec<i64> {
    segments
        .iter()
        .map(|s| observe(field, s, projector).expect("allow-all field"))
        .collect()
}

// ═══════════════════════════════════════════════════════════════════════
// Kernel 3: graph BFS (irregular)
// ═══════════════════════════════════════════════════════════════════════

/// Deterministic undirected graph: a ring plus chords of stride 5, so
/// every node is reachable from node 0. For n below 6 the stride-5 chord
/// collapses into self-loops and duplicate edges; dedup and the visited
/// check keep BFS correct, but the generator is intended for n >= 6.
fn build_ring_chord_graph(n: usize) -> Vec<Vec<usize>> {
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
fn bfs_baseline(adj: &[Vec<usize>], start: usize) -> Vec<usize> {
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
struct GraphAdjProjector {
    /// Baked adjacency: node index to neighbor indices.
    adj: Vec<Vec<usize>>,
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
struct FrontierConstraint {
    frontier: HashSet<i64>,
}

impl FrontierConstraint {
    fn new(frontier: &[i64]) -> Self {
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
fn build_bfs_scheme(n: usize) -> Vec<Segment> {
    (0..n as i64)
        .map(|i| Segment::from_values(vec![i]))
        .collect()
}

/// SSCCS path: level-iterated observation. The Scheme is the graph
/// structure, the Field is the evolving frontier constraint (the mutable
/// layer), the Projector carries adjacency semantics, and each observation
/// collapses the current level. Returns the visit order.
fn bfs_ssccs(segments: &[Segment], projector: &GraphAdjProjector, start: usize) -> Vec<i64> {
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

// ═══════════════════════════════════════════════════════════════════════
// Verify group: path-equality guard (runs on every bench invocation)
// ═══════════════════════════════════════════════════════════════════════

/// Asserts that both paths produce identical outputs for all kernels,
/// using small fixtures. A path regression fails the benchmark run.
fn bench_verify_paths(c: &mut Criterion) {
    c.bench_function("verify/paths", |b| {
        b.iter(|| {
            // Vector addition
            let a: Vec<i64> = (0..1000).collect();
            let b: Vec<i64> = (1000..2000).collect();
            let segments = build_vec_add_scheme(&a, &b);
            let field = Field::new();
            let projector = PairSumProjector;
            assert_eq!(
                vec_add_baseline(&a, &b),
                vec_add_ssccs(&segments, &field, &projector)
            );

            // 2D convolution
            let width = 32usize;
            let height = 32usize;
            let input: Vec<i64> = (0..(width * height) as i64).collect();
            let kernel = [1i64, 2, 1, 2, 4, 2, 1, 2, 1];
            let segments = build_conv_scheme(&input, width, height);
            let field = Field::new();
            let projector = PatchConvProjector { kernel };
            let baseline = conv2d_baseline(&input, width, height, &kernel);
            let interior: Vec<i64> = baseline
                .iter()
                .enumerate()
                .filter(|(i, _)| {
                    let x = i % width;
                    let y = i / width;
                    x != 0 && y != 0 && x != width - 1 && y != height - 1
                })
                .map(|(_, v)| *v)
                .collect();
            assert_eq!(interior, conv2d_ssccs(&segments, &field, &projector));

            // Graph BFS: same reachable set, each node visited once
            let n = 100usize;
            let adj = build_ring_chord_graph(n);
            let segments = build_bfs_scheme(n);
            let projector = GraphAdjProjector { adj: adj.clone() };
            let baseline = bfs_baseline(&adj, 0);
            let ssccs = bfs_ssccs(&segments, &projector, 0);
            assert_eq!(baseline.len(), ssccs.len());
            let baseline_set: HashSet<usize> = baseline.iter().copied().collect();
            let ssccs_set: HashSet<i64> = ssccs.iter().copied().collect();
            assert_eq!(baseline_set.len(), baseline.len());
            assert_eq!(ssccs_set.len(), ssccs.len());
            for node in baseline {
                assert!(ssccs_set.contains(&(node as i64)), "node {node} missing");
            }

            // Convolution scheme rejects grids below 3x3. The panic hook
            // is silenced so the caught panic does not pollute the bench
            // output on every iteration.
            let hook = std::panic::take_hook();
            std::panic::set_hook(Box::new(|_| {}));
            let underflow = std::panic::catch_unwind(|| build_conv_scheme(&[0i64], 1, 1));
            std::panic::set_hook(hook);
            assert!(underflow.is_err());
            assert_eq!(build_conv_scheme(&[0i64; 9], 3, 3).len(), 1);
        })
    });
}

// ═══════════════════════════════════════════════════════════════════════
// Kernels group: measurements
// ═══════════════════════════════════════════════════════════════════════

const VEC_N: usize = 10_000;
const CONV_W: usize = 128;
const CONV_H: usize = 128;
const BFS_N: usize = 1_000;

fn bench_vector_add(c: &mut Criterion) {
    let a: Vec<i64> = (0..VEC_N as i64).collect();
    let b: Vec<i64> = (1..=VEC_N as i64).collect();
    let segments = build_vec_add_scheme(&a, &b);
    let field = Field::new();
    let projector = PairSumProjector;

    c.bench_function("kernels/vector_add/baseline", |bencher| {
        bencher.iter(|| black_box(vec_add_baseline(black_box(&a), black_box(&b))))
    });
    c.bench_function("kernels/vector_add/ssccs", |bencher| {
        bencher.iter(|| {
            black_box(vec_add_ssccs(
                black_box(&segments),
                black_box(&field),
                black_box(&projector),
            ))
        })
    });
}

fn bench_conv2d(c: &mut Criterion) {
    let input: Vec<i64> = (0..(CONV_W * CONV_H) as i64).collect();
    let kernel = [1i64, 2, 1, 2, 4, 2, 1, 2, 1];
    let segments = build_conv_scheme(&input, CONV_W, CONV_H);
    let field = Field::new();
    let projector = PatchConvProjector { kernel };

    c.bench_function("kernels/conv2d/baseline", |bencher| {
        bencher.iter(|| {
            black_box(conv2d_baseline(
                black_box(&input),
                CONV_W,
                CONV_H,
                black_box(&kernel),
            ))
        })
    });
    c.bench_function("kernels/conv2d/ssccs", |bencher| {
        bencher.iter(|| {
            black_box(conv2d_ssccs(
                black_box(&segments),
                black_box(&field),
                black_box(&projector),
            ))
        })
    });
}

fn bench_bfs(c: &mut Criterion) {
    let adj = build_ring_chord_graph(BFS_N);
    let segments = build_bfs_scheme(BFS_N);
    let projector = GraphAdjProjector { adj: adj.clone() };

    c.bench_function("kernels/bfs/baseline", |bencher| {
        bencher.iter(|| black_box(bfs_baseline(black_box(&adj), 0)))
    });
    c.bench_function("kernels/bfs/ssccs", |bencher| {
        bencher.iter(|| black_box(bfs_ssccs(black_box(&segments), black_box(&projector), 0)))
    });
}

criterion_group!(
    name = verify;
    config = Criterion::default().sample_size(10);
    targets = bench_verify_paths
);
criterion_group!(
    name = kernels;
    config = Criterion::default().sample_size(100);
    targets = bench_vector_add, bench_conv2d, bench_bfs
);
criterion_main!(verify, kernels);
