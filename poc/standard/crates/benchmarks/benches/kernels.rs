//! Validation-only benchmark suite for the three reference simulation
//! kernels. Each kernel runs as a pure Rust baseline and as the SSCCS
//! formulation; the measured ratio is the emulation overhead on existing
//! hardware, recorded as validation evidence for the practical plane.

use criterion::{Criterion, criterion_group, criterion_main};
use ssccs_benchmarks::{
    GraphAdjProjector, PairSumProjector, PatchConvProjector, bfs_baseline, bfs_ssccs,
    build_bfs_scheme, build_conv_scheme, build_ring_chord_graph, build_vec_add_scheme,
    conv2d_baseline, conv2d_ssccs, vec_add_baseline, vec_add_ssccs,
};
use ssccs_core::Field;
use std::hint::black_box;

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

    c.bench_function("vector_add/baseline", |bencher| {
        bencher.iter(|| black_box(vec_add_baseline(black_box(&a), black_box(&b))))
    });
    c.bench_function("vector_add/ssccs", |bencher| {
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

    c.bench_function("conv2d/baseline", |bencher| {
        bencher.iter(|| {
            black_box(conv2d_baseline(
                black_box(&input),
                CONV_W,
                CONV_H,
                black_box(&kernel),
            ))
        })
    });
    c.bench_function("conv2d/ssccs", |bencher| {
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

    c.bench_function("bfs/baseline", |bencher| {
        bencher.iter(|| black_box(bfs_baseline(black_box(&adj), 0)))
    });
    c.bench_function("bfs/ssccs", |bencher| {
        bencher.iter(|| black_box(bfs_ssccs(black_box(&segments), black_box(&projector), 0)))
    });
}

criterion_group!(kernels, bench_vector_add, bench_conv2d, bench_bfs);
criterion_main!(kernels);
