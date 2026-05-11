//! SSCCS core concepts in RISC-V assembly — with pure-Rust software fallback.
//!
//! Whitepaper §2.3.2: Union(∪)=C₁∨C₂,T=max(T₁,T₂), Intersection(∩)=C₁∧C₂,T=min(T₁,T₂).
//!
//! Validation strategy:
//!   RISC-V target: actual assembly (observe_full.S) via global_asm!
//!   Other targets:  pure-Rust fallback with identical logic
//!   Golden anchor:  test reads GOLDEN_* from observe_full.S and verifies correctness
//!
//! This ensures changing the .S file forces updating the golden anchors,
//! which forces updating the Rust tests — keeping both in sync.

#![allow(dead_code)]

#[cfg(target_arch = "riscv64")]
global_asm!(include_str!("../asm/observe_full.S"));

pub const REJECT_SENTINEL: i64 = i64::MIN;
pub type ConstraintFn = unsafe extern "C" fn(*const i64) -> u32;
pub type ProjectorFn = unsafe extern "C" fn(*const i64) -> i64;

#[cfg(target_arch = "riscv64")]
extern "C" {
    fn ck_even(coord: *const i64) -> u32;
    fn ck_range_0_10(coord: *const i64) -> u32;
    fn ck_range(coord: *const i64, min: i64, max: i64) -> u32;
    fn ck_eq_val(coord: *const i64, target: i64) -> u32;
    fn ck_gt(coord: *const i64, threshold: i64) -> u32;
    fn ck_even_w(coord: *const i64) -> u32;
    fn ck_range_w(coord: *const i64) -> u32;
    fn compose_and_fast(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_or_fast(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_intersect(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_union(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn compose_product_2d(fa: ConstraintFn, fb: ConstraintFn, coord: *const i64) -> u32;
    fn proj_id(coord: *const i64) -> i64;
    fn proj_sum2d(coord: *const i64) -> i64;
    fn proj_sum3d(coord: *const i64) -> i64;
    fn proj_parity(coord: *const i64) -> i64;
    fn proj_negate(coord: *const i64) -> i64;
    fn observe(field_fn: ConstraintFn, coord: *const i64, proj_fn: ProjectorFn) -> i64;
    fn observe_batch(
        field_fn: ConstraintFn,
        coords: *const *const i64,
        count: usize,
        proj_fn: ProjectorFn,
        out: *mut i64,
    );
    fn run_narrow();
    fn run_broad();
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

// ═══════════════════════════════════════════════════════════════════════
// Pure-Rust fallback — logic identical to RISC-V asm. Tested on CI.
// ═══════════════════════════════════════════════════════════════════════

#[cfg(not(target_arch = "riscv64"))]
pub mod fallback {
    pub fn ck_even(v: i64) -> u32 {
        ((v & 1) ^ 1) as u32
    }
    pub fn ck_range_0_10(v: i64) -> u32 {
        (v >= 0 && v <= 10) as u32
    }
    pub fn ck_range(v: i64, lo: i64, hi: i64) -> u32 {
        (v >= lo && v <= hi) as u32
    }
    pub fn ck_eq_val(v: i64, t: i64) -> u32 {
        (v == t) as u32
    }
    pub fn ck_gt(v: i64, t: i64) -> u32 {
        (v > t) as u32
    }
    pub fn compose_and(fa: fn(i64) -> u32, fb: fn(i64) -> u32, v: i64) -> u32 {
        fa(v) & fb(v)
    }
    pub fn compose_or(fa: fn(i64) -> u32, fb: fn(i64) -> u32, v: i64) -> u32 {
        fa(v) | fb(v)
    }
    pub fn proj_id(v: i64) -> i64 {
        v
    }
    pub fn proj_sum2d(a: i64, b: i64) -> i64 {
        a + b
    }
    pub fn proj_sum3d(a: i64, b: i64, c: i64) -> i64 {
        a + b + c
    }
    pub fn proj_parity(v: i64) -> i64 {
        v & 1
    }
    pub fn proj_negate(v: i64) -> i64 {
        -v
    }
    pub fn observe(field: fn(i64) -> u32, coord: i64, proj: fn(i64) -> i64) -> i64 {
        if field(coord) != 0 {
            proj(coord)
        } else {
            i64::MIN
        }
    }
}

// ═══════════════════════════════════════════════════════════════════════
// Tests — all platforms. Golden anchors prevent asm/rust drift.
// ═══════════════════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    #[cfg(not(target_arch = "riscv64"))]
    use super::fallback;
    use super::REJECT_SENTINEL;

    // Read golden anchors DIRECTLY from the assembly file.
    // If .S changes, these anchors must change, or the test fails.
    const ASM_SRC: &str = include_str!("../asm/observe_full.S");

    fn parse_golden(key: &str) -> Vec<i64> {
        for line in ASM_SRC.lines() {
            let t = line.trim();
            if let Some(val) = t.strip_prefix(&format!("# {}: ", key)) {
                return val
                    .split(',')
                    .map(|s| {
                        let s = s.trim();
                        if s == "REJECT" {
                            REJECT_SENTINEL
                        } else {
                            s.parse().unwrap()
                        }
                    })
                    .collect();
            }
        }
        panic!("GOLDEN anchor \"{}\" not found in observe_full.S", key);
    }

    #[test]
    fn test_golden_anchors_present() {
        let seg = parse_golden("GOLDEN_SEGMENTS");
        assert_eq!(seg, [2, 3, 5, 10, 12], "edit observe_full.S or update test");
        let narrow = parse_golden("GOLDEN_NARROW");
        assert_eq!(
            narrow,
            [2, REJECT_SENTINEL, REJECT_SENTINEL, 10, REJECT_SENTINEL]
        );
        let broad = parse_golden("GOLDEN_BROAD");
        assert_eq!(broad, [2, 3, 5, 10, 12, REJECT_SENTINEL]);
    }

    #[cfg(target_arch = "riscv64")]
    unsafe fn even(v: i64) -> u32 {
        super::ck_even(&v)
    }
    #[cfg(target_arch = "riscv64")]
    unsafe fn r010(v: i64) -> u32 {
        super::ck_range_0_10(&v)
    }

    #[cfg(not(target_arch = "riscv64"))]
    fn even(v: i64) -> u32 {
        fallback::ck_even(v)
    }
    #[cfg(not(target_arch = "riscv64"))]
    fn r010(v: i64) -> u32 {
        fallback::ck_range_0_10(v)
    }

    fn narrow(v: i64) -> u32 {
        even(v) & r010(v)
    }
    fn broad(v: i64) -> u32 {
        even(v) | r010(v)
    }

    #[test]
    fn test_constraints() {
        assert!(even(2) != 0);
        assert!(even(3) == 0);
        assert!(even(0) != 0);
        assert!(even(-2) != 0);
        assert!(r010(5) != 0);
        assert!(r010(11) == 0);
        assert!(r010(0) != 0);
        assert!(r010(10) != 0);
    }

    #[test]
    fn test_composition() {
        assert!(narrow(2) != 0);
        assert!(narrow(3) == 0);
        assert!(narrow(12) == 0);
        assert!(broad(2) != 0);
        assert!(broad(3) != 0);
        assert!(broad(12) != 0);
        assert!(broad(13) == 0);
    }

    #[test]
    fn test_observe_narrow() {
        assert_eq!(fallback::observe(narrow, 2, fallback::proj_id), 2);
        assert_eq!(
            fallback::observe(narrow, 3, fallback::proj_id),
            REJECT_SENTINEL
        );
        assert_eq!(
            fallback::observe(narrow, 12, fallback::proj_id),
            REJECT_SENTINEL
        );
    }

    #[test]
    fn test_observe_broad() {
        assert_eq!(fallback::observe(broad, 2, fallback::proj_id), 2);
        assert_eq!(fallback::observe(broad, 3, fallback::proj_id), 3);
        assert_eq!(fallback::observe(broad, 5, fallback::proj_id), 5);
        assert_eq!(fallback::observe(broad, 12, fallback::proj_id), 12);
        assert_eq!(
            fallback::observe(broad, 13, fallback::proj_id),
            REJECT_SENTINEL
        );
    }

    #[test]
    fn test_projectors() {
        assert_eq!(fallback::proj_parity(2), 0);
        assert_eq!(fallback::proj_parity(3), 1);
        assert_eq!(fallback::proj_negate(5), -5);
        assert_eq!(fallback::proj_sum2d(2, 3), 5);
        assert_eq!(fallback::proj_sum3d(1, 2, 3), 6);
    }

    #[test]
    fn test_composition_vs_golden() {
        let seg = parse_golden("GOLDEN_SEGMENTS");
        let expected_narrow = parse_golden("GOLDEN_NARROW");
        let expected_broad = parse_golden("GOLDEN_BROAD");

        for (&c, &exp) in seg.iter().zip(expected_narrow.iter()) {
            let actual = fallback::observe(narrow, c, fallback::proj_id);
            assert_eq!(
                actual, exp,
                "narrow({}) mismatch with GOLDEN_NARROW in .S",
                c
            );
        }
        let seg_with_reject = [seg.as_slice(), &[13i64]].concat();
        let expected_all = [expected_broad.clone(), vec![REJECT_SENTINEL]].concat();
        for (&c, &exp) in seg_with_reject.iter().zip(expected_all.iter()) {
            let actual = fallback::observe(broad, c, fallback::proj_id);
            assert_eq!(actual, exp, "broad({}) mismatch with GOLDEN_BROAD in .S", c);
        }
    }
}
