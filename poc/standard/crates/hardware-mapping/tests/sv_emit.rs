//! What the emitter writes, read against the modules it instantiates.
//!
//! The checks are on the emitted text because that is what crosses the boundary into a substrate: a bound, a join and
//! a unit name are decisions only the text can show. `make -C sv generated-check` and `elaborate` are what say the
//! text is a design.

use ssccs_core::ConstraintSpec;
use ssccs_hardware_mapping::{ComposeOp, ConstraintProgram, ProjectorUnit, emit_observation_sv};

fn narrow() -> ConstraintProgram {
    ConstraintProgram {
        constraints: vec![
            ConstraintSpec::Even,
            ConstraintSpec::Range { min: 0, max: 10 },
        ],
        compose: ComposeOp::And,
    }
}

#[test]
fn bounds_are_baked_in_their_two_complement_form() {
    let sv = emit_observation_sv(
        "m",
        &ConstraintProgram {
            constraints: vec![ConstraintSpec::Range { min: -2, max: 10 }],
            compose: ComposeOp::And,
        },
        ProjectorUnit::Identity,
    );
    assert!(sv.contains(".min_val(64'hfffffffffffffffe)"), "{sv}");
    assert!(sv.contains(".max_val(64'h000000000000000a)"), "{sv}");
}

#[test]
fn kinds_instantiate_the_units_that_carry_them() {
    let sv = emit_observation_sv("m", &narrow(), ProjectorUnit::Identity);
    assert!(sv.contains("    ck_even u_c0 ("), "{sv}");
    assert!(sv.contains("    ck_range u_c1 ("), "{sv}");
    assert!(sv.contains(".min_val(64'h0000000000000000)"), "{sv}");
    assert!(sv.contains(".max_val(64'h000000000000000a)"), "{sv}");
}

#[test]
fn the_declared_join_is_the_gate_that_is_emitted() {
    let and = emit_observation_sv("m", &narrow(), ProjectorUnit::Identity);
    assert!(and.contains("wire constraint_result = c0 && c1;"), "{and}");

    let or = emit_observation_sv(
        "m",
        &ConstraintProgram {
            compose: ComposeOp::Or,
            ..narrow()
        },
        ProjectorUnit::Identity,
    );
    assert!(or.contains("wire constraint_result = c0 || c1;"), "{or}");
}

#[test]
fn an_empty_program_admits_the_whole_space() {
    let sv = emit_observation_sv(
        "m",
        &ConstraintProgram {
            constraints: Vec::new(),
            compose: ComposeOp::And,
        },
        ProjectorUnit::Identity,
    );
    assert!(sv.contains("wire constraint_result = 1'b1;"), "{sv}");
    assert!(!sv.contains("u_c0"), "{sv}");
}

#[test]
fn the_projection_and_the_reject_rule_are_the_units_not_copies() {
    let sv = emit_observation_sv("m", &narrow(), ProjectorUnit::Parity);
    assert!(sv.contains("    proj_parity u_projector ("), "{sv}");
    assert!(sv.contains("    observe u_observe ("), "{sv}");
    assert!(sv.contains(".projection(projection)"), "{sv}");
    assert!(sv.contains(".valid(valid)"), "{sv}");
    // The sentinel belongs to observe. An emitter that wrote it would be a second definition of the reject rule.
    assert!(!sv.contains("8000000000000000"), "{sv}");
}
