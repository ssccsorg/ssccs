//! A Scheme's address map, as decode logic.
//!
//! The whitepaper's mapping stage hands a fabric the logical-address map as decode logic: an address in, the
//! coordinate it names out. A Scheme's coordinates form a product of axis ranges, so that map is arithmetic over
//! the extents, and this module derives the extents from the Scheme's own segments rather than from a declaration
//! written beside it.
//!
//! A coordinate's address is its mixed-radix index with the last axis varying fastest, which is the order the
//! Scheme templates enumerate in. A Scheme whose segments are not that product is refused: a decoder over an
//! arbitrary set would be a table, and the table is what the map is meant to replace.
//!
//! A coordinate is an i64, so an offset may be negative and is written as its two's complement pattern. The
//! arithmetic below is unsigned on those patterns, which is exact because two's complement addition and
//! multiplication do not depend on the reading of the sign bit.

use std::collections::BTreeSet;

use ssccs_core::Coordinates;
use ssccs_primitive::SchemeTrait;

/// One axis of the product, as the Scheme's segments imply it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AxisExtent {
    pub name: String,
    /// The lowest value on the axis.
    pub offset: i64,
    /// The distance between neighbours.
    pub rate: i64,
    /// How many values the axis carries.
    pub size: u64,
}

/// Why a Scheme has no arithmetic address map.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum DecodeError {
    /// The Scheme has no segments, so it has no address space.
    Empty,
    /// A segment does not carry one value per axis.
    Ragged { segment: usize, axes: usize },
    /// An axis's values are not equally spaced.
    NotArithmetic { axis: usize },
    /// The segments are not exactly the product of the axes' extents.
    NotAProduct { segments: usize, product: u64 },
}

impl std::fmt::Display for DecodeError {
    fn fmt(&self, formatter: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            DecodeError::Empty => write!(formatter, "the Scheme has no segments"),
            DecodeError::Ragged { segment, axes } => {
                write!(formatter, "segment {segment} does not carry {axes} values")
            }
            DecodeError::NotArithmetic { axis } => {
                write!(formatter, "axis {axis} is not equally spaced")
            }
            DecodeError::NotAProduct { segments, product } => write!(
                formatter,
                "{segments} segments where the extents multiply to {product}"
            ),
        }
    }
}

/// The extents a Scheme's segments imply, in axis order.
pub fn axis_extents(scheme: &impl SchemeTrait) -> Result<Vec<AxisExtent>, DecodeError> {
    let axes = scheme.axes().len();
    let mut values: Vec<BTreeSet<i64>> = vec![BTreeSet::new(); axes];
    let mut segments = 0usize;

    for (index, segment) in scheme.segments().enumerate() {
        let raw = &segment.coordinates().raw;
        if raw.len() != axes {
            return Err(DecodeError::Ragged {
                segment: index,
                axes: raw.len(),
            });
        }
        for (axis, value) in raw.iter().enumerate() {
            values[axis].insert(*value);
        }
        segments += 1;
    }

    if segments == 0 {
        return Err(DecodeError::Empty);
    }

    let mut extents = Vec::with_capacity(axes);
    for (axis, distinct) in values.iter().enumerate() {
        let sorted: Vec<i64> = distinct.iter().copied().collect();
        let rate = match sorted.len() {
            0 => return Err(DecodeError::Empty),
            1 => 1,
            _ => {
                let rate = sorted[1] - sorted[0];
                if sorted.windows(2).any(|pair| pair[1] - pair[0] != rate) {
                    return Err(DecodeError::NotArithmetic { axis });
                }
                rate
            }
        };

        let name = scheme
            .axes()
            .get(axis)
            .map(|axis| axis.name.clone())
            .unwrap_or_else(|| format!("axis{axis}"));

        extents.push(AxisExtent {
            name,
            offset: sorted[0],
            rate,
            size: sorted.len() as u64,
        });
    }

    let product: u64 = extents.iter().map(|extent| extent.size).product();
    if product != segments as u64 {
        return Err(DecodeError::NotAProduct { segments, product });
    }

    Ok(extents)
}

/// The address a coordinate occupies, or `None` when it is not one the extents describe.
pub fn address_of(extents: &[AxisExtent], coords: &Coordinates) -> Option<u64> {
    if coords.raw.len() != extents.len() {
        return None;
    }

    let mut index = 0u64;
    for (axis, extent) in extents.iter().enumerate() {
        let stride: u64 = extents[axis + 1..]
            .iter()
            .map(|following| following.size)
            .product();
        let delta = coords.raw[axis] - extent.offset;
        if delta % extent.rate != 0 {
            return None;
        }
        let position = delta / extent.rate;
        if position < 0 || position as u64 >= extent.size {
            return None;
        }
        index += position as u64 * stride;
    }

    Some(index)
}

/// The width an address of `total` entries needs, never narrower than one bit.
pub fn address_bits(total: u64) -> usize {
    if total <= 1 {
        1
    } else {
        64 - (total - 1).leading_zeros() as usize
    }
}

/// Write the module that decodes an address into the coordinate the Scheme holds there.
///
/// The output count follows the axis count, so the module's ports are a function of the Scheme. `valid` is low for
/// an address past the last segment, which is a point the Scheme does not have rather than a point computed wrong.
pub fn emit_address_decode_sv(
    module: &str,
    scheme: &impl SchemeTrait,
) -> Result<String, DecodeError> {
    let extents = axis_extents(scheme)?;
    let total: u64 = extents.iter().map(|extent| extent.size).product();
    let width = address_bits(total);

    let mut sv = String::new();
    sv.push_str(
        "// Generated by ssccs-hardware-mapping. The emitter is the source of this file.\n",
    );
    sv.push_str("//\n");
    sv.push_str(&format!(
        "// Scheme: {} axes, {} segments, with the last axis varying fastest.\n",
        extents.len(),
        total
    ));
    for extent in &extents {
        sv.push_str(&format!(
            "// {}: {} values from {}, step {}\n",
            extent.name, extent.size, extent.offset, extent.rate
        ));
    }
    sv.push_str("//\n");
    sv.push_str("// A coordinate is an i64, so the offsets are two's complement patterns and the arithmetic is\n");
    sv.push_str("// unsigned on those patterns.\n\n");

    sv.push_str(&format!("module {module} (\n"));
    sv.push_str(&format!("    input  logic [{}:0] addr,\n", width - 1));
    for axis in 0..extents.len() {
        sv.push_str(&format!("    output logic [63:0] coord{axis},\n"));
    }
    sv.push_str("    output logic        valid\n");
    sv.push_str(");\n\n");

    sv.push_str("    wire [63:0] index;\n");
    sv.push_str("    assign index = addr;\n\n");
    sv.push_str(&format!("    assign valid = index < 64'd{total};\n"));

    for (axis, extent) in extents.iter().enumerate() {
        let stride: u64 = extents[axis + 1..]
            .iter()
            .map(|following| following.size)
            .product();

        let mut value = if stride == 1 {
            "index".to_string()
        } else {
            format!("(index / 64'd{stride})")
        };

        // The quotient is already bounded when the remaining axes fill the space.
        if stride * extent.size != total {
            value = format!("({value} % 64'd{})", extent.size);
        }

        if extent.rate != 1 {
            value = format!("({value} * 64'h{:016x})", extent.rate as u64);
        }

        if extent.offset != 0 {
            value = format!("({value} + 64'h{:016x})", extent.offset as u64);
        }

        sv.push_str(&format!("\n    // {}\n", extent.name));
        sv.push_str(&format!("    assign coord{axis} = {value};\n"));
    }

    sv.push_str("\nendmodule\n");
    Ok(sv)
}
