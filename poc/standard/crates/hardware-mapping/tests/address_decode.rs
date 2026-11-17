//! A Scheme's address map, checked against the Scheme's own segments.
//!
//! The emitter turns extents into arithmetic. These cases compare that arithmetic against the segments the Scheme
//! holds, so a wrong stride, rate or offset shows up as a coordinate at the wrong address.

use ssccs_core::Segment;
use ssccs_hardware_mapping::{
    AxisExtent, DecodeError, address_bits, address_of, axis_extents, emit_address_decode_sv,
};
use ssccs_primitive::{Axis, AxisType, GridTopology, SchemeBuilder};
use ssccs_schemes::{Grid2DTemplate, IntegerLineTemplate, Tensor3DTemplate};

fn axis(name: &str) -> Axis {
    Axis {
        name: name.to_string(),
        axis_type: AxisType::Discrete,
        metadata: Default::default(),
    }
}

/// The coordinate the emitted arithmetic names at `index`, computed from the extents.
fn decode(extents: &[AxisExtent], index: u64) -> Option<Vec<i64>> {
    let mut remaining = index;
    let mut coords = vec![0i64; extents.len()];

    for (position, extent) in extents.iter().enumerate().rev() {
        let offset = remaining % extent.size;
        remaining /= extent.size;
        coords[position] = extent.offset + offset as i64 * extent.rate;
    }

    if remaining != 0 {
        return None;
    }
    Some(coords)
}

#[test]
fn a_line_decodes_to_its_values() {
    let scheme = IntegerLineTemplate::new(0, 9, 1).build();
    let extents = axis_extents(&scheme).expect("a line is a product");

    assert_eq!(extents.len(), 1);
    assert_eq!(extents[0].offset, 0);
    assert_eq!(extents[0].rate, 1);
    assert_eq!(extents[0].size, 10);
    assert_eq!(address_bits(10), 4);

    for index in 0..10u64 {
        assert_eq!(decode(&extents, index), Some(vec![index as i64]));
    }
}

#[test]
fn a_strided_line_keeps_its_step() {
    let scheme = IntegerLineTemplate::new(0, 10, 2).build();
    let extents = axis_extents(&scheme).expect("a strided line is a product");

    assert_eq!(extents[0].rate, 2);
    assert_eq!(extents[0].size, 6);

    for index in 0..6u64 {
        assert_eq!(decode(&extents, index), Some(vec![2 * index as i64]));
    }
}

#[test]
fn a_negative_offset_is_kept() {
    let scheme = IntegerLineTemplate::new(-5, 5, 1).build();
    let extents = axis_extents(&scheme).expect("a shifted line is a product");
    assert_eq!(extents[0].offset, -5);
    assert_eq!(decode(&extents, 0), Some(vec![-5]));

    let sv = emit_address_decode_sv("decode", &scheme).expect("the line decodes");
    assert!(
        sv.contains("64'hfffffffffffffffb"),
        "the offset is its two's complement pattern: {sv}"
    );
}

#[test]
fn a_grid_decodes_with_the_last_axis_fastest() {
    let scheme = Grid2DTemplate::new(4, 3, GridTopology::FourConnected).build();
    let extents = axis_extents(&scheme).expect("a grid is a product");

    assert_eq!(extents.len(), 2);
    assert_eq!(extents[0].size, 4);
    assert_eq!(extents[1].size, 3);

    assert_eq!(decode(&extents, 0), Some(vec![0, 0]));
    assert_eq!(decode(&extents, 3), Some(vec![1, 0]));
    assert_eq!(decode(&extents, 4), Some(vec![1, 1]));

    let sv = emit_address_decode_sv("decode", &scheme).expect("the grid decodes");
    assert!(sv.contains("assign coord0 = (index / 64'd3)"), "{sv}");
    assert!(sv.contains("assign coord1 = (index % 64'd3)"), "{sv}");
    assert!(sv.contains("assign valid = index < 64'd12;"), "{sv}");
}

#[test]
fn a_tensor_decodes_over_three_axes() {
    let scheme = Tensor3DTemplate::new(2, 3, 4).build();
    let extents = axis_extents(&scheme).expect("a tensor is a product");

    assert_eq!(extents.len(), 3);
    assert_eq!(extents[0].size, 2);
    assert_eq!(extents[1].size, 3);
    assert_eq!(extents[2].size, 4);
    assert_eq!(decode(&extents, 7), Some(vec![0, 1, 3]));

    let sv = emit_address_decode_sv("decode", &scheme).expect("the tensor decodes");
    assert!(sv.contains("assign coord0 = (index / 64'd12)"), "{sv}");
    assert!(
        sv.contains("assign coord1 = ((index / 64'd4) % 64'd3)"),
        "{sv}"
    );
    assert!(sv.contains("assign coord2 = (index % 64'd4)"), "{sv}");
}

#[test]
fn a_hole_in_the_space_is_refused() {
    let scheme = SchemeBuilder::new()
        .add_axis(axis("x"))
        .add_axis(axis("y"))
        .add_segment(&Segment::from_values(vec![0, 0]))
        .add_segment(&Segment::from_values(vec![0, 1]))
        .add_segment(&Segment::from_values(vec![1, 0]))
        .build();

    assert_eq!(
        axis_extents(&scheme),
        Err(DecodeError::NotAProduct {
            segments: 3,
            product: 4
        })
    );
    assert!(emit_address_decode_sv("decode", &scheme).is_err());
}

#[test]
fn an_uneven_axis_is_refused() {
    let scheme = SchemeBuilder::new()
        .add_axis(axis("x"))
        .add_segment(&Segment::from_value(0))
        .add_segment(&Segment::from_value(1))
        .add_segment(&Segment::from_value(3))
        .build();

    assert_eq!(
        axis_extents(&scheme),
        Err(DecodeError::NotArithmetic { axis: 0 })
    );
}

#[test]
fn a_scheme_without_segments_is_refused() {
    let scheme = SchemeBuilder::new().add_axis(axis("x")).build();
    assert_eq!(axis_extents(&scheme), Err(DecodeError::Empty));
}

#[test]
fn the_address_is_the_inverse_of_the_decode() {
    let scheme = Grid2DTemplate::new(4, 3, GridTopology::EightConnected).build();
    let extents = axis_extents(&scheme).expect("a grid is a product");

    let mut seen = [false; 12];
    for segment in scheme.segments() {
        let index =
            address_of(&extents, segment.coordinates()).expect("every segment has an address");
        let slot = &mut seen[index as usize];
        assert!(!*slot, "two segments landed at address {index}");
        *slot = true;
        assert_eq!(
            decode(&extents, index),
            Some(segment.coordinates().raw.clone())
        );
    }

    assert!(
        seen.iter().all(|occupied| *occupied),
        "the addresses cover the space"
    );
}
