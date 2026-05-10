//! SSCCS core concepts in RISC-V assembly.
//!
//! Embeds the observation pipeline directly in hardware instructions:
//! constraint-check → projector-call → result, or reject sentinel.
//!
//! Includes the assembly via `global_asm!` and provides typed Rust wrappers.

use core::arch::global_asm;

global_asm!(include_str!("../asm/observe.S"));

/// Sentinel returned when a constraint rejects a coordinate.
pub const REJECT_SENTINEL: i64 = i64::MIN;

extern "C" {
    // constraint checks
    fn check_even(coord: *const i64) -> u32;
    fn check_range_0_10(coord: *const i64) -> u32;

    // field composition in hardware
    fn compose_and(fa: unsafe extern "C" fn(*const i64) -> u32,
                   fb: unsafe extern "C" fn(*const i64) -> u32,
                   coord: *const i64) -> u32;
    fn compose_or(fa: unsafe extern "C" fn(*const i64) -> u32,
                  fb: unsafe extern "C" fn(*const i64) -> u32,
                  coord: *const i64) -> u32;

    // projector
    fn projector_identity(coord: *const i64) -> i64;

    // core observation
    fn observe(field_fn: unsafe extern "C" fn(*const i64) -> u32,
               coord: *const i64,
               projector_fn: unsafe extern "C" fn(*const i64) -> i64) -> i64;

    // static segments
    static SEGMENT_0: i64;
    static SEGMENT_1: i64;
    static SEGMENT_2: i64;
}

/// A constraint function: takes a pointer to a coordinate, returns 1 if allowed.
pub type ConstraintFn = unsafe extern "C" fn(*const i64) -> u32;
/// A projector function: takes a pointer to a coordinate, returns the projection.
pub type ProjectorFn = unsafe extern "C" fn(*const i64) -> i64;

/// Run a single observation.
///
/// Returns `Some(projection)` if the coordinate passes all constraints,
/// `None` if rejected.
pub fn observe_one(
    constraint: ConstraintFn,
    coord: &i64,
    projector: ProjectorFn,
) -> Option<i64> {
    let result = unsafe { observe(constraint, coord, projector) };
    if result == REJECT_SENTINEL { None } else { Some(result) }
}

/// Compose two constraint functions with AND (intersection).
pub fn field_and(a: ConstraintFn, b: ConstraintFn) -> impl Fn(&i64) -> bool {
    move |coord: &i64| unsafe { compose_and(a, b, coord) != 0 }
}

/// Compose two constraint functions with OR (union).
pub fn field_or(a: ConstraintFn, b: ConstraintFn) -> impl Fn(&i64) -> bool {
    move |coord: &i64| unsafe { compose_or(a, b, coord) != 0 }
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Provide a safe wrapper for calling constraints from Rust tests.
    unsafe fn check(f: ConstraintFn, coord: &i64) -> bool {
        f(coord) != 0
    }

    #[test]
    fn test_check_even() {
        let two: i64 = 2;
        let three: i64 = 3;
        unsafe {
            assert!(check(check_even, &two));
            assert!(!check(check_even, &three));
        }
    }

    #[test]
    fn test_check_range() {
        let v5: i64 = 5;
        let v11: i64 = 11;
        unsafe {
            assert!(check(check_range_0_10, &v5));
            assert!(!check(check_range_0_10, &v11));
        }
    }

    #[test]
    fn test_compose_and_or() {
        let coord_2: i64 = 2;
        let coord_3: i64 = 3;
        let coord_12: i64 = 12;

        unsafe {
            // even ∧ range → narrow
            assert!(compose_and(check_even, check_range_0_10, &coord_2) != 0);
            assert!(compose_and(check_even, check_range_0_10, &coord_3) == 0);
            assert!(compose_and(check_even, check_range_0_10, &coord_12) == 0);

            // even ∨ range → broad
            assert!(compose_or(check_even, check_range_0_10, &coord_2) != 0);
            assert!(compose_or(check_even, check_range_0_10, &coord_3) != 0);
            assert!(compose_or(check_even, check_range_0_10, &coord_12) != 0);
        }
    }

    #[test]
    fn test_observe_narrow() {
        // Narrow field: even ∧ range.  Observe static segments.
        unsafe {
            let r0 = observe(compose_and, &SEGMENT_0, projector_identity);
            let r1 = observe(compose_and, &SEGMENT_1, projector_identity);
            let r2 = observe(compose_and, &SEGMENT_2, projector_identity);
            assert_eq!(r0, 2);                             // even, in range → projected
            assert_eq!(r1, REJECT_SENTINEL);                // odd → rejected
            assert_eq!(r2, REJECT_SENTINEL);                // out of range → rejected
        }
    }

    #[test]
    fn test_observe_broad() {
        // Broad field: even ∨ range.
        unsafe {
            let r0 = observe(compose_or, &SEGMENT_0, projector_identity);
            let r1 = observe(compose_or, &SEGMENT_1, projector_identity);
            let r2 = observe(compose_or, &SEGMENT_2, projector_identity);
            assert_eq!(r0, 2);                             // even, in range
            assert_eq!(r1, 3);                             // odd, but in range → projected
            assert_eq!(r2, REJECT_SENTINEL);                // out of range, not even → rejected
        }
    }
}
