//! Assembly data section emitter for the reference simulation.
//!
//! Bakes a Scheme structure into assembly `.rodata` tables, following the
//! conventions of `baremetal_riscv/asm/observe_full.S`: one label per
//! segment, a combined coordinate table, a logical address table, and
//! golden anchor comments. The emitted text is the immutable structure of
//! the Scheme as data, consumable by the observation routines.
//!
//! The output is deterministic: the same Scheme always produces the same
//! text, because segments are ordered by coordinates, never by hash map
//! iteration. This is the materialization of the open format thesis on the
//! reference simulation: the structure is baked, not interpreted.

use ssccs_core::Segment;
use ssccs_primitive::scheme::abstract_scheme::Scheme;

/// The emitted assembly data section.
pub struct EmittedDataSection {
    /// Full `.S` text of the data section.
    pub text: String,
}

/// Emits the immutable structure of a Scheme as an assembly `.rodata`
/// section: a header, axis metadata comments, one label per segment, a
/// combined coordinate table, a logical address table, and golden anchor
/// comments.
///
/// The emitted layout:
///
/// ```text
/// SCHEME_SEG_COUNT:   .8byte <n>
/// SEG_0:              .8byte <c0>, <c1>, ...
/// SEG_1:              ...
/// SCHEME_COORDS:      .8byte SEG_0, SEG_1, ...
/// SCHEME_ADDRESSES:   .8byte <offset0>, <offset1>, ...
/// ```
///
/// The coordinate table and the address table share one ordering: the
/// segment order determined by lexicographic coordinate sort. A segment
/// without a logical address emits `0`, and the table is preceded by a
/// note when any segment is unmapped. An empty scheme emits zero
/// placeholders so the table labels stay well-defined.
pub fn emit_scheme_data(scheme: &Scheme) -> EmittedDataSection {
    let mut segments: Vec<&Segment> = scheme.segments().collect();
    segments.sort_by(|a, b| a.coordinates().raw.cmp(&b.coordinates().raw));

    let mut out = String::new();
    out.push_str("# SSCCS reference simulation: Scheme baked as data\n");
    out.push_str(&format!("# SchemeId: {}\n", hex::encode(scheme.id().0)));
    out.push_str(&format!("# Axes: {}\n", emit_axis_line(scheme)));
    out.push_str(&format!("# Segments: {}\n", segments.len()));
    out.push('\n');

    out.push_str(".section .rodata\n");
    out.push_str(".align 3\n\n");

    out.push_str(&format!(
        ".globl SCHEME_SEG_COUNT\nSCHEME_SEG_COUNT: .8byte {}\n\n",
        segments.len()
    ));

    for (idx, segment) in segments.iter().enumerate() {
        let coords = segment
            .coordinates()
            .raw
            .iter()
            .map(|v| v.to_string())
            .collect::<Vec<_>>()
            .join(", ");
        out.push_str(&format!(".globl SEG_{idx}\nSEG_{idx}: .8byte {coords}\n"));
    }
    out.push('\n');

    let labels = (0..segments.len())
        .map(|idx| format!("SEG_{idx}"))
        .collect::<Vec<_>>()
        .join(", ");
    if segments.is_empty() {
        // An empty scheme must still produce well-defined labels. A zero
        // placeholder keeps the tables addressable, and consumers are
        // guarded by SCHEME_SEG_COUNT.
        out.push_str(
            ".globl SCHEME_COORDS\nSCHEME_COORDS: .8byte 0   # empty scheme placeholder\n\n",
        );
        out.push_str(
            ".globl SCHEME_ADDRESSES\nSCHEME_ADDRESSES: .8byte 0   # empty scheme placeholder\n\n",
        );
    } else {
        out.push_str(&format!(
            ".globl SCHEME_COORDS\nSCHEME_COORDS: .8byte {labels}\n\n"
        ));
    }

    let mut addresses = Vec::with_capacity(segments.len());
    let mut unmapped = false;
    for segment in &segments {
        match scheme.map_to_logical_address(segment.coordinates()) {
            Some(addr) => addresses.push(addr.offset.to_string()),
            None => {
                unmapped = true;
                addresses.push("0".to_string());
            }
        }
    }
    let addr_line = addresses.join(", ");
    if unmapped {
        out.push_str("# NOTE: unmapped segments emit address 0\n");
    }
    if !segments.is_empty() {
        out.push_str(&format!(
            ".globl SCHEME_ADDRESSES\nSCHEME_ADDRESSES: .8byte {addr_line}\n\n"
        ));
    }

    emit_golden_anchors(&mut out, &segments, &addresses);

    EmittedDataSection { text: out }
}

/// Emits the axis description as a comment line.
fn emit_axis_line(scheme: &Scheme) -> String {
    scheme
        .axes()
        .iter()
        .map(|axis| axis.name.clone())
        .collect::<Vec<_>>()
        .join(",")
}

/// Emits golden anchor comments, one per segment, so the assembly path and
/// the host path can be checked for agreement in CI.
fn emit_golden_anchors(out: &mut String, segments: &[&Segment], addresses: &[String]) {
    out.push_str("# GOLDEN TEST ANCHORS, parsed by Rust tests\n");
    let dim = segments
        .first()
        .map(|s| s.coordinates().raw.len())
        .unwrap_or(0);
    out.push_str(&format!("# GOLDEN_DIM: {dim}\n"));
    out.push_str(&format!("# GOLDEN_COUNT: {}\n", segments.len()));
    for (idx, segment) in segments.iter().enumerate() {
        let coords = segment
            .coordinates()
            .raw
            .iter()
            .map(|v| v.to_string())
            .collect::<Vec<_>>()
            .join(",");
        out.push_str(&format!("# GOLDEN_SEG_{idx}: {coords}\n"));
    }
    out.push_str(&format!("# GOLDEN_ADDRESSES: {}\n", addresses.join(",")));
}
