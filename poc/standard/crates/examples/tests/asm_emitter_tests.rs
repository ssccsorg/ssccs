//! Integration tests for the assembly data section emitter.
//!
//! The emitter bakes a Scheme structure into assembly `.rodata` tables.
//! These tests verify determinism, coordinate ordering, address agreement
//! with the Scheme layout mapping, and golden anchor emission.

use ssccs_core::{Coordinates, Segment};
use ssccs_examples::asm_emitter::emit_scheme_data;
use ssccs_primitive::scheme::abstract_scheme::{Axis, AxisType, Scheme, SchemeBuilder};

/// An integer line scheme mirroring the static data of `observe_full.S`.
fn integer_line_scheme() -> Scheme {
    let mut builder = SchemeBuilder::new().add_axis(Axis {
        name: "x".to_string(),
        axis_type: AxisType::Discrete,
        metadata: Default::default(),
    });
    for v in [2i64, 3, 5, 10, 12] {
        builder = builder.add_segment(&Segment::from_values(vec![v]));
    }
    builder.build()
}

#[test]
fn emission_is_deterministic() {
    let scheme = integer_line_scheme();
    let a = emit_scheme_data(&scheme);
    let b = emit_scheme_data(&scheme);
    assert_eq!(a.text, b.text);
}

#[test]
fn emission_contains_sorted_segment_labels() {
    let scheme = integer_line_scheme();
    let out = emit_scheme_data(&scheme).text;
    // Segments must be sorted by coordinates: 2,3,5,10,12.
    let pos_2 = out.find("SEG_0: .8byte 2").expect("SEG_0 value");
    let pos_3 = out.find("SEG_1: .8byte 3").expect("SEG_1 value");
    let pos_5 = out.find("SEG_2: .8byte 5").expect("SEG_2 value");
    let pos_10 = out.find("SEG_3: .8byte 10").expect("SEG_3 value");
    let pos_12 = out.find("SEG_4: .8byte 12").expect("SEG_4 value");
    assert!(pos_2 < pos_3 && pos_3 < pos_5 && pos_5 < pos_10 && pos_10 < pos_12);
}

#[test]
fn emission_has_combined_table_and_count() {
    let scheme = integer_line_scheme();
    let out = emit_scheme_data(&scheme).text;
    assert!(out.contains("SCHEME_SEG_COUNT: .8byte 5"));
    assert!(out.contains("SCHEME_COORDS: .8byte SEG_0, SEG_1, SEG_2, SEG_3, SEG_4"));
    assert!(out.contains("SCHEME_ADDRESSES: .8byte"));
}

#[test]
fn emission_matches_logical_addresses() {
    let scheme = integer_line_scheme();
    let out = emit_scheme_data(&scheme).text;
    let expected: Vec<String> = [2i64, 3, 5, 10, 12]
        .iter()
        .map(|v| {
            scheme
                .map_to_logical_address(&Coordinates::new(vec![*v]))
                .expect("mapped")
                .offset
                .to_string()
        })
        .collect();
    assert!(out.contains(&format!("SCHEME_ADDRESSES: .8byte {}", expected.join(", "))));
}

#[test]
fn emission_carries_golden_anchors() {
    let scheme = integer_line_scheme();
    let out = emit_scheme_data(&scheme).text;
    assert!(out.contains("# GOLDEN_DIM: 1"));
    assert!(out.contains("# GOLDEN_COUNT: 5"));
    assert!(out.contains("# GOLDEN_SEG_0: 2"));
    assert!(out.contains("# GOLDEN_SEG_4: 12"));
}

#[test]
fn multi_dim_emission_flattens_coordinates() {
    let mut builder = SchemeBuilder::new()
        .add_axis(Axis {
            name: "x".to_string(),
            axis_type: AxisType::Discrete,
            metadata: Default::default(),
        })
        .add_axis(Axis {
            name: "y".to_string(),
            axis_type: AxisType::Discrete,
            metadata: Default::default(),
        });
    for (x, y) in [(2i64, 1i64), (1, 2), (0, 3)] {
        builder = builder.add_segment(&Segment::from_values(vec![x, y]));
    }
    let scheme = builder.build();
    let out = emit_scheme_data(&scheme).text;
    // Sorted lexicographically: (0,3), (1,2), (2,1).
    assert!(out.contains("SEG_0: .8byte 0, 3"));
    assert!(out.contains("SEG_1: .8byte 1, 2"));
    assert!(out.contains("SEG_2: .8byte 2, 1"));
    assert!(out.contains("# GOLDEN_DIM: 2"));
}

#[test]
fn empty_scheme_emits_zero_count() {
    let scheme = SchemeBuilder::new().build();
    let out = emit_scheme_data(&scheme).text;
    assert!(out.contains("SCHEME_SEG_COUNT: .8byte 0"));
    assert!(out.contains("# GOLDEN_COUNT: 0"));
}

#[test]
fn pipeline_stage_emits_assembly_text() {
    use ssccs_examples::compiler_pipeline::{CompilerPipeline, HardwareProfile};
    let scheme = integer_line_scheme();
    let compiled = CompilerPipeline::new(scheme, HardwareProfile::Cpu { cores: 1 }).compile();
    let text = String::from_utf8(compiled.observation_code).expect("assembly text");
    assert!(text.contains(".section .rodata"));
    assert!(text.contains("SCHEME_COORDS"));
}

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

/// Parses the segment coordinate values from the emitted golden anchors.
fn emitted_segments(text: &str) -> Vec<i64> {
    let count = parse_golden(text, "GOLDEN_COUNT")[0] as usize;
    (0..count)
        .map(|i| parse_golden(text, &format!("GOLDEN_SEG_{i}"))[0])
        .collect()
}

/// The assembly contract: the emitted generated tables must reproduce the
/// same structure and the same observation projections as the golden anchors
/// in `baremetal_riscv/asm/observe_full.S` (GOLDEN_SCHEME_*).
#[test]
fn generated_tables_drive_observation_matching_assembly_golden() {
    use ssccs_core::{Coordinates, Field, Segment, observe};
    use ssccs_examples::constraints::{EvenConstraint, RangeConstraint};
    use ssccs_examples::projectors::IntegerProjector;

    let scheme = integer_line_scheme();
    let out = emit_scheme_data(&scheme).text;

    // The emitted structure must carry the assembly contract values.
    let segs = emitted_segments(&out);
    assert_eq!(segs, [2, 3, 5, 10, 12]);

    // Narrow observation: even AND range [0,10], via the real model
    // machinery over the generated data.
    let mut narrow_field = Field::new();
    narrow_field.add_constraint(EvenConstraint::new(0));
    narrow_field.add_constraint(RangeConstraint::new(0, 0, 10));
    let projector = IntegerProjector::new(0);
    let reject = i64::MIN;
    let got_narrow: Vec<i64> = segs
        .iter()
        .map(|&v| {
            let segment = Segment::from_values(vec![v]);
            observe(&narrow_field, &segment, &projector).unwrap_or(reject)
        })
        .collect();
    assert_eq!(got_narrow, [2, reject, reject, 10, reject]);

    // Broad observation: even OR range [0,10], union semantics.
    let got_broad: Vec<i64> = segs
        .iter()
        .map(|&v| {
            let even = v % 2 == 0;
            let in_range = (0..=10).contains(&v);
            if even || in_range { v } else { reject }
        })
        .collect();
    assert_eq!(got_broad, [2, 3, 5, 10, 12]);
}
