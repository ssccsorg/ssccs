//! Branchless constraint gate emitter for the reference simulation.
//!
//! Lowers declarative constraint specs into RISC-V assembly functions with
//! baked constants and zero conditional branches, following the ABI of the
//! hand-written gates in `baremetal_riscv/asm/observe_full.S`:
//! `fn(*const i64) -> u32` with the coordinate pointer in `a0` and the
//! gate result in `a0`. A gate is the Field constraint substrate lowered
//! to instruction sequences: comparison and mask only, no branching.
//!
//! `eval_constraint` is the host-side semantic reference of the same
//! specs. Golden anchors emitted with each gate record the reference
//! results over a caller-provided fixture, so the generated assembly and
//! the host path are pinned to the same semantics.
//!
//! Connection contract: a generated gate is a drop-in `field_fn` for the
//! observation routines (`observe_scheme` / `observe_batch`), with the
//! same ABI. Wiring the gate emission into the compiler pipeline is the
//! next milestone; until then the host path consumes the specs directly
//! through `eval_constraint`, and the tests pin both sides to the same
//! golden results.

/// Declarative constraint spec on the pure plane.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstraintSpec {
    /// Coordinate value is even.
    Even,
    /// Coordinate value within inclusive bounds.
    Range { min: i64, max: i64 },
    /// Coordinate value equals a constant.
    Eq { value: i64 },
    /// Coordinate value strictly greater than a constant.
    Gt { value: i64 },
}

/// Host-side semantic reference of a constraint gate.
pub fn eval_constraint(spec: &ConstraintSpec, value: i64) -> bool {
    match spec {
        ConstraintSpec::Even => value % 2 == 0,
        ConstraintSpec::Range { min, max } => *min <= value && value <= *max,
        ConstraintSpec::Eq { value: target } => value == *target,
        ConstraintSpec::Gt { value: threshold } => value > *threshold,
    }
}

/// Emits one branchless constraint gate as a `.S` function with the
/// constants baked in. The generated function has no conditional branches.
pub fn emit_constraint_gate(spec: &ConstraintSpec, label: &str) -> String {
    let mut out = String::new();
    out.push_str(&format!(".globl {label}\n{label}:\n"));
    out.push_str("    ld      t0, 0(a0)           # load i64\n");
    match spec {
        ConstraintSpec::Even => {
            out.push_str("    andi    t0, t0, 1           # mask LSB\n");
            out.push_str("    xori    a0, t0, 1           # 1=even, 0=odd\n");
        }
        ConstraintSpec::Range { min, max } => {
            out.push_str(&format!("    li      t1, {min}\n"));
            out.push_str("    slt     t2, t0, t1          # coord < min\n");
            out.push_str(&format!("    li      t1, {max}\n"));
            out.push_str("    slt     t3, t1, t0          # max < coord\n");
            out.push_str("    or      t2, t2, t3          # out of range\n");
            out.push_str("    xori    a0, t2, 1           # 1=in range\n");
        }
        ConstraintSpec::Eq { value } => {
            out.push_str(&format!("    li      t1, {value}\n"));
            out.push_str("    xor     t0, t0, t1          # difference\n");
            out.push_str("    seqz    a0, t0              # 1=equal\n");
        }
        ConstraintSpec::Gt { value } => {
            out.push_str(&format!("    li      t1, {value}\n"));
            out.push_str("    slt     a0, t1, t0          # 1=value < coord\n");
        }
    }
    out.push_str("    ret\n");
    out
}

/// Emits a batch of branchless constraint gates with golden anchors.
///
/// Each gate gets a `# GOLDEN_GATE_<label>: <results>` comment recording
/// `eval_constraint` over the provided fixture, so tests can pin the
/// generated assembly to the host reference.
pub fn emit_constraint_gates<S: AsRef<str>>(
    specs: &[(S, ConstraintSpec)],
    fixture: &[i64],
) -> String {
    let mut out = String::new();
    out.push_str("# Generated branchless constraint gates, reference simulation\n");
    out.push_str("# ABI: fn(*const i64) -> u32, coordinate pointer in a0, result in a0\n\n");
    out.push_str(".section .text\n");
    for (label, spec) in specs {
        out.push_str(&format!("# Constraint: {spec:?}\n"));
        out.push_str(&emit_constraint_gate(spec, label.as_ref()));
        out.push('\n');
    }
    for (label, spec) in specs {
        let results = fixture
            .iter()
            .map(|v| u8::from(eval_constraint(spec, *v)).to_string())
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!("# GOLDEN_GATE_{}: {results}\n", label.as_ref()));
    }
    out
}
