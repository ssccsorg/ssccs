//! Correctness tests for the validation-only benchmarking kernels.
//!
//! Each kernel must produce identical outputs on both paths, so the
//! benchmark compares like for like: the pure Rust baseline and the SSCCS
//! reference simulation over the same input.

use ssccs_benchmarks::{
    GraphAdjProjector, PairSumProjector, PatchConvProjector, bfs_baseline, bfs_ssccs,
    build_bfs_scheme, build_conv_scheme, build_ring_chord_graph, build_vec_add_scheme,
    conv2d_baseline, conv2d_ssccs, vec_add_baseline, vec_add_ssccs,
};
use ssccs_core::Field;
use std::collections::HashSet;

#[test]
fn vector_add_paths_are_identical() {
    let a: Vec<i64> = (0..1000).collect();
    let b: Vec<i64> = (1000..2000).collect();
    let segments = build_vec_add_scheme(&a, &b);
    let field = Field::new();
    let projector = PairSumProjector;

    let baseline = vec_add_baseline(&a, &b);
    let ssccs = vec_add_ssccs(&segments, &field, &projector);
    assert_eq!(baseline, ssccs);
}

#[test]
fn conv2d_paths_are_identical() {
    let width = 32usize;
    let height = 32usize;
    let input: Vec<i64> = (0..(width * height) as i64).collect();
    let kernel = [1i64, 2, 1, 2, 4, 2, 1, 2, 1];
    let segments = build_conv_scheme(&input, width, height);
    let field = Field::new();
    let projector = PatchConvProjector { kernel };

    let baseline = conv2d_baseline(&input, width, height, &kernel);
    let ssccs = conv2d_ssccs(&segments, &field, &projector);

    // The baseline output includes the untouched border (width * height
    // entries with zero border); the scheme covers only interior pixels.
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
    assert_eq!(interior, ssccs);
}

#[test]
fn bfs_paths_reach_the_same_nodes() {
    let n = 500usize;
    let adj = build_ring_chord_graph(n);
    let segments = build_bfs_scheme(n);
    let projector = GraphAdjProjector { adj: adj.clone() };

    let baseline = bfs_baseline(&adj, 0);
    let ssccs = bfs_ssccs(&segments, &projector, 0);

    assert_eq!(baseline.len(), ssccs.len());
    let baseline_set: HashSet<usize> = baseline.iter().copied().collect();
    let ssccs_set: HashSet<i64> = ssccs.iter().copied().collect();
    assert_eq!(
        baseline_set.len(),
        baseline.len(),
        "baseline visits each node once"
    );
    assert_eq!(ssccs_set.len(), ssccs.len(), "ssccs visits each node once");
    for node in baseline {
        assert!(ssccs_set.contains(&(node as i64)), "node {node} missing");
    }
}
