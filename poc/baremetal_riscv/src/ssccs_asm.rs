#![allow(dead_code)]
//! SSCCS core concepts in RISC-V assembly — the full observation pipeline.
//!
//! Whitepaper §2.3.2: Union(∪)=C₁∨C₂,T=max(T₁,T₂), Intersection(∩)=C₁∧C₂,T=min(T₁,T₂).
//!
//! Assembly files: asm/observe_full.S

#![allow(unused_imports)]

use core::arch::global_asm;

#[cfg(target_arch = "riscv64")]
global_asm!(include_str!("../asm/observe_full.S"));

pub const REJECT_SENTINEL: i64 = i64::MIN;

// Constraint function: coord_ptr → 1(allowed) | 0(rejected)
pub type ConstraintFn = unsafe extern "C" fn(*const i64) -> u32;
// Projector function: coord_ptr → projection value
pub type ProjectorFn = unsafe extern "C" fn(*const i64) -> i64;

#[cfg(target_arch = "riscv64")]
extern "C" {
    // branchless constraints
    fn ck_even(coord: *const i64) -> u32;
    fn ck_range_0_10(coord: *const i64) -> u32;
    fn ck_range(coord: *const i64, min: i64, max: i64) -> u32;
    fn ck_eq_val(coord: *const i64, target: i64) -> u32;
    fn ck_gt(coord: *const i64, threshold: i64) -> u32;

    // weighted constraints (return weight in fa0)
    fn ck_even_w(coord: *const i64) -> u32;
    fn ck_range_w(coord: *const i64) -> u32;

    // constraint-only composition
    fn compose_and_fast(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_or_fast(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;

    // weighted composition (returns weight in fa0)
    fn compose_intersect(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_union(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_product_2d(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;

    // projectors
    fn proj_id(coord: *const i64) -> i64;
    fn proj_sum2d(coord: *const i64) -> i64;
    fn proj_sum3d(coord: *const i64) -> i64;
    fn proj_parity(coord: *const i64) -> i64;
    fn proj_negate(coord: *const i64) -> i64;

    // observation pipeline
    fn observe(field_fn: ConstraintFn, coord: *const i64, proj_fn: ProjectorFn) -> i64;
    fn observe_batch(
        field_fn: ConstraintFn,
        coords: *const *const i64,
        count: usize,
        proj_fn: ProjectorFn,
        out: *mut i64,
    );

    // scenario runners (self-contained demos)
    fn run_narrow();
    fn run_broad();

    // static segments (immutable structure)
    static SEG_0: i64;
    static SEG_1: i64;
    static SEG_2: i64;
    static SEG_3: i64;
    static SEG_4: i64;
    static BATCH_COORDS: [*const i64; 5];
    static NARROW_RESULTS: [i64; 5];
    static BROAD_RESULTS: [i64; 5];
    static SEG_3D_A: [i64; 3];
    static SEG_3D_B: [i64; 3];
}

#[cfg(target_arch = "riscv64")]
pub fn observe_one(field: ConstraintFn, coord: &i64, proj: ProjectorFn) -> Option<i64> {
    let r = unsafe { observe(field, coord, proj) };
    if r == REJECT_SENTINEL {
        None
    } else {
        Some(r)
    }
}

#[cfg(target_arch = "riscv64")]
pub fn narrow_results() -> &'static [i64; 5] {
    unsafe { &NARROW_RESULTS }
}

#[cfg(target_arch = "riscv64")]
pub fn broad_results() -> &'static [i64; 5] {
    unsafe { &BROAD_RESULTS }
}

#[cfg(target_arch = "riscv64")]
mod tests {
    use super::*;

    #[test]
    fn test_narrow_vs_broad() {
        unsafe {
            run_narrow();
            run_broad();
            // Narrow: even ∧ range → SEG_0(2)✓, SEG_1(3)✗, SEG_2(5)✗, SEG_3(10)✓, SEG_4(12)✗
            assert_eq!(NARROW_RESULTS[0], 2);
            assert_eq!(NARROW_RESULTS[1], REJECT_SENTINEL);
            assert_eq!(NARROW_RESULTS[2], REJECT_SENTINEL);
            assert_eq!(NARROW_RESULTS[3], 10);
            assert_eq!(NARROW_RESULTS[4], REJECT_SENTINEL);
            // Broad: even ∨ range → all except SEG_4(12)
            assert_eq!(BROAD_RESULTS[0], 2);
            assert_eq!(BROAD_RESULTS[1], 3);
            assert_eq!(BROAD_RESULTS[2], 5);
            assert_eq!(BROAD_RESULTS[3], 10);
            assert_eq!(BROAD_RESULTS[4], REJECT_SENTINEL);
        }
    }
}
