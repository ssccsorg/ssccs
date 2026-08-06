//! Integration tests for the branchless constraint gate emitter.
//!
//! The emitter lowers declarative constraint specs into RISC-V assembly
//! functions with baked constants and zero conditional branches. These
//! tests verify the generated instruction patterns, the golden anchor
//! agreement with the hand-written `observe_full.S` semantics, agreement
//! with the existing constraint machinery, and the observation connection.

use ssccs_core::{Field, Segment};
use ssccs_examples::constraint_emitter::{
    eval_constraint, emit_constraint_gate, emit_constraint_gates, ConstraintSpec,
};
use ssccs_examples::constraints::{EvenConstraint, RangeConstraint};

/// The standard fixture shared with `observe_full.S`.
const FIXTURE: [i64; 5] = [2, 3, 5, 10, 12];

/// Parses a `GOLDEN_*` anchor line from the emitted text.
fn parse_golden(text: &str, key: &str) -> Vec<i64> {
    for line in text.lines() {
        let t = line.trim();
        if let Some(val) = t.strip_prefix(&format!("# {key}: ")) {
            return val.split(',').map(|s| s.trim().parse().unwrap()).collect();
        }
    }
    panic!("golden anchor {key} not found");
}

/// Returns true when the gate text contains a conditional branch.
fn has_conditional_branch(text: &str) -> bool {
    text.lines().any(|l| {
        let t = l.trim();
        t.starts_with("beq ")
            || t.starts_with("bne ")
            || t.starts_with("blt ")
            || t.starts_with("bge ")
            || t.starts_with("bltu ")
            || t.starts_with("bgeu ")
    })
}

#[test]
fn even_gate_is_branchless_and_matches_handwritten_pattern() {
    let gate = emit_constraint_gate(&ConstraintSpec::Even, "gen_even");
    assert!(gate.contains("andi    t0, t0, 1"));
    assert!(gate.contains("xori    a0, t0, 1"));
    assert!(!has_conditional_branch(&gate));
}

#[test]
fn range_gate_bakes_bounds() {
    let gate = emit_constraint_gate(&ConstraintSpec::Range { min: 0, max: 10 }, "gen_range");
    assert!(gate.contains("li      t1, 0"));
    assert!(gate.contains("li      t1, 10"));
    assert!(gate.contains("slt     t2, t0, t1"));
    assert!(gate.contains("slt     t3, t1, t0"));
    assert!(!has_conditional_branch(&gate));
}

#[test]
fn eq_and_gt_gates_bake_constants() {
    let eq = emit_constraint_gate(&ConstraintSpec::Eq { value: 3 }, "gen_eq");
    assert!(eq.contains("li      t1, 3"));
    assert!(eq.contains("seqz    a0, t0"));
    assert!(!has_conditional_branch(&eq));

    let gt = emit_constraint_gate(&ConstraintSpec::Gt { value: 4 }, "gen_gt");
    assert!(gt.contains("li      t1, 4"));
    assert!(gt.contains("slt     a0, t1, t0"));
    assert!(!has_conditional_branch(&gt));
}

#[test]
fn generated_gates_golden_agree_with_handwritten_semantics() {
    let specs = [
        ("gen_even", ConstraintSpec::Even),
        ("gen_range", ConstraintSpec::Range { min: 0, max: 10 }),
        ("gen_eq", ConstraintSpec::Eq { value: 3 }),
        ("gen_gt", ConstraintSpec::Gt { value: 4 }),
    ];
    let text = emit_constraint_gates(&specs, &FIXTURE);
    // Expected results follow the hand-written gates in observe_full.S:
    // even over 2,3,5,10,12 -> 1,0,0,1,1
    // range [0,10]           -> 1,1,1,1,0  (12 out)
    // eq 3                   -> 0,1,0,0,0
    // gt 4                   -> 0,0,1,1,1
    assert_eq!(parse_golden(&text, "GOLDEN_GATE_gen_even"), [1, 0, 0, 1, 1]);
    assert_eq!(parse_golden(&text, "GOLDEN_GATE_gen_range"), [1, 1, 1, 1, 0]);
    assert_eq!(parse_golden(&text, "GOLDEN_GATE_gen_eq"), [0, 1, 0, 0, 0]);
    assert_eq!(parse_golden(&text, "GOLDEN_GATE_gen_gt"), [0, 0, 1, 1, 1]);
}

#[test]
fn eval_constraint_agrees_with_existing_constraint_machinery() {
    let mut field = Field::new();
    field.add_constraint(EvenConstraint::new(0));
    field.add_constraint(RangeConstraint::new(0, 0, 10));
    for v in FIXTURE {
        let segment = Segment::from_values(vec![v]);
        let allows = field.allows(segment.coordinates());
        let even = eval_constraint(&ConstraintSpec::Even, v);
        let range = eval_constraint(&ConstraintSpec::Range { min: 0, max: 10 }, v);
        assert_eq!(allows, even && range, "value {v}");
    }
}

#[test]
fn generated_gates_drive_narrow_observation() {
    // Narrow observation: even AND range [0,10], using the gate reference
    // as the field. Must reproduce the assembly golden GOLDEN_SCHEME_NARROW.
    let reject = i64::MIN;
    let narrow: Vec<i64> = FIXTURE
        .iter()
        .map(|&v| {
            let even = eval_constraint(&ConstraintSpec::Even, v);
            let range = eval_constraint(&ConstraintSpec::Range { min: 0, max: 10 }, v);
            if even && range {
                v
            } else {
                reject
            }
        })
        .collect();
    assert_eq!(narrow, [2, reject, reject, 10, reject]);
}
