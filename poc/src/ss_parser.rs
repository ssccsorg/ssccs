//! Parser for the `.ss` binary format.
//!
//! The binary format directly reflects the `MemoryLayout` abstraction and
//! includes a header, axis definitions, segment table, relation graph,
//! memory‑layout description, observation rules, and structural constraints.
//!
//! This module provides a `parse` function that reads a binary blob and
//! reconstructs a `Scheme` instance.

use crate::core::Segment;
use crate::scheme::abstract_scheme::{Axis, AxisType, Scheme, SchemeBuilder};
use std::collections::HashMap;
use std::io::{Read, Seek};

/// Error type for parsing failures.
#[derive(Debug, thiserror::Error)]
pub enum ParseError {
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Invalid magic number")]
    InvalidMagic,
    #[error("Unsupported version: {0}")]
    UnsupportedVersion(u8),
    #[error("Malformed data: {0}")]
    Malformed(String),
}

/// Parses a binary `.ss` stream into a `Scheme`.
///
/// The stream must implement `Read + Seek`. The parser validates the header,
/// reads all sections, and builds a `Scheme` using the `SchemeBuilder`.
pub fn parse<R: Read + Seek>(mut reader: R) -> Result<Scheme, ParseError> {
    // 1. Header
    let mut magic = [0u8; 4];
    reader.read_exact(&mut magic)?;
    if &magic != b".ss\0" {
        return Err(ParseError::InvalidMagic);
    }
    let version = {
        let mut buf = [0u8; 1];
        reader.read_exact(&mut buf)?;
        buf[0]
    };
    if version != 1 {
        return Err(ParseError::UnsupportedVersion(version));
    }

    // For now, we return a dummy Scheme.
    // TODO: implement full parsing of axis, segment, relation, memory layout,
    // observation rules, and constraints.
    let dummy_scheme = SchemeBuilder::new()
        .add_axis(Axis {
            name: "x".to_string(),
            axis_type: AxisType::Discrete,
            metadata: HashMap::new(),
        })
        .add_segment(Segment::from_values(vec![0]))
        .build();

    Ok(dummy_scheme)
}

/// Serializes a `Scheme` into the binary `.ss` format.
///
/// This is a placeholder; a real implementation would write the header,
/// axis list, segment table, relation graph, memory‑layout description,
/// observation rules, and structural constraints.
pub fn serialize<W: std::io::Write>(_scheme: &Scheme, _writer: W) -> Result<(), ParseError> {
    todo!("Binary serialization not yet implemented")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Cursor;

    #[test]
    fn test_parse_dummy() {
        // Create a minimal valid binary header (magic + version)
        let mut data = vec![];
        data.extend_from_slice(b".ss\0");
        data.push(1); // version

        let cursor = Cursor::new(data);
        let result = parse(cursor);
        assert!(result.is_ok());
    }

    #[test]
    fn test_parse_invalid_magic() {
        let data = vec![0u8; 10];
        let cursor = Cursor::new(data);
        let result = parse(cursor);
        assert!(matches!(result, Err(ParseError::InvalidMagic)));
    }
}
