//! SSCCS core concepts in x86-64 AT&T assembly with SSE2 SIMD.
//!
//! Branchless constraint evaluation, 4-way SIMD batch checks,
//! field composition, and the full observation pipeline.

#![cfg(target_arch = "x86_64")]
#![allow(dead_code)]

use core::arch::global_asm;

global_asm!(include_str!("../../../asm/observe_x86.S"));

pub const REJECT_SENTINEL: i64 = i64::MIN;
pub type ConstraintFn = unsafe extern "C" fn(*const i64) -> u32;
pub type ProjectorFn = unsafe extern "C" fn(*const i64) -> i64;

#[allow(dead_code)]
unsafe extern "C" {
    fn ck_even(coord: *const i64) -> u32;
    fn ck_range_0_10(coord: *const i64) -> u32;
    fn ck_gt(coord: *const i64, threshold: i64) -> u32;
    fn ck_range_4way(coord: *const i64, min: i64, max: i64) -> u32;
    fn ck_even_4way(coord: *const i64) -> u32;
    fn compose_and(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_or(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_3way_and(
        fa: ConstraintFn,
        fb: ConstraintFn,
        fc: ConstraintFn,
        coord: *const i64,
    ) -> u32;
    fn proj_id(coord: *const i64) -> i64;
    fn proj_sum2d(coord: *const i64) -> i64;
    fn proj_sum3d(coord: *const i64) -> i64;
    fn proj_parity(coord: *const i64) -> i64;
    fn observe(field_fn: ConstraintFn, coord: *const i64, proj_fn: ProjectorFn) -> i64;
    fn observe_batch(
        field_fn: ConstraintFn,
        coords: *const *const i64,
        count: usize,
        proj_fn: ProjectorFn,
        out: *mut i64,
    );
    static SEG_0: i64;
    static SEG_1: i64;
    static SEG_2: i64;
    static SEG_3: i64;
    static SEG_4: i64;
    static SEG_4WAY: [i64; 4];
    static BATCH_TABLE: [*const i64; 5];
    static NARROW_RESULTS: [i64; 5];
    static BROAD_RESULTS: [i64; 5];
}

pub fn observe_one(field: ConstraintFn, coord: &i64, proj: ProjectorFn) -> Option<i64> {
    let r = unsafe { observe(field, coord, proj) };
    if r == REJECT_SENTINEL { None } else { Some(r) }
}

pub fn field_and(a: ConstraintFn, b: ConstraintFn) -> impl Fn(&i64) -> bool {
    move |c: &i64| unsafe { compose_and(a, b, c) != 0 }
}
pub fn field_or(a: ConstraintFn, b: ConstraintFn) -> impl Fn(&i64) -> bool {
    move |c: &i64| unsafe { compose_or(a, b, c) != 0 }
}

#[cfg(test)]
mod tests {
    use super::*;

    extern "C" fn narrow_even_range(coord: *const i64) -> u32 {
        unsafe { compose_and(ck_even, ck_range_0_10, coord) }
    }
    extern "C" fn broad_even_range(coord: *const i64) -> u32 {
        unsafe { compose_or(ck_even, ck_range_0_10, coord) }
    }

    #[test]
    fn test_constraints() {
        unsafe {
            assert!(ck_even(&2) != 0);
            assert!(ck_even(&3) == 0);
            assert!(ck_range_0_10(&5) != 0);
            assert!(ck_range_0_10(&11) == 0);
            assert!(ck_range_0_10(&0) != 0);
            assert!(ck_range_0_10(&10) != 0);
            assert!(ck_gt(&10, 5) != 0);
            assert!(ck_gt(&3, 5) == 0);
        }
    }

    #[test]
    fn test_simd_4way() {
        unsafe {
            let mask = ck_range_4way(SEG_4WAY.as_ptr(), 0, 10);
            assert_eq!(mask & 0b1011, 0b1011);
            assert_eq!(mask & 0b0100, 0);
            let mask_even = ck_even_4way(SEG_4WAY.as_ptr());
            assert_eq!(mask_even & 0b1011, 0b1011);
            assert_eq!(mask_even & 0b0100, 0);
        }
    }

    #[test]
    fn test_observe_narrow() {
        unsafe {
            assert_eq!(observe(narrow_even_range, &SEG_0, proj_id), 2);
            assert_eq!(observe(narrow_even_range, &SEG_1, proj_id), REJECT_SENTINEL);
            assert_eq!(observe(narrow_even_range, &SEG_4, proj_id), REJECT_SENTINEL);
        }
    }

    #[test]
    fn test_observe_broad() {
        unsafe {
            assert_eq!(observe(broad_even_range, &SEG_0, proj_id), 2);
            assert_eq!(observe(broad_even_range, &SEG_1, proj_id), 3);
            assert_eq!(observe(broad_even_range, &SEG_2, proj_id), 5);
            assert_eq!(observe(broad_even_range, &SEG_4, proj_id), REJECT_SENTINEL);
        }
    }

    #[test]
    fn test_observe_identity() {
        let r2 = observe_one(ck_even, &2, proj_id);
        let r3 = observe_one(ck_even, &3, proj_id);
        assert_eq!(r2, Some(2));
        assert_eq!(r3, None);
    }

    #[test]
    fn test_projectors() {
        unsafe {
            assert_eq!(proj_parity(&SEG_0), 0);
            assert_eq!(proj_parity(&SEG_1), 1);
        }
    }
}
