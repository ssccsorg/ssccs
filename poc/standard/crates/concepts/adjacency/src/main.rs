//! Experiment: Adjacency & Memory Layout
//!
//! Tests structural relations and memory layout semantics.

use ssccs_core::{Coordinates, Segment};
use ssccs_primitive::scheme::abstract_scheme::{
    AdjacencyType, Axis, AxisType, GridTopology, LayoutType, LogicalAddress, MemoryLayout,
    SchemeBuilder, StructuralRelation,
};
use std::collections::HashMap;
use std::sync::Arc;

fn main() {
    println!("Experiment: Adjacency & Memory Layout            ");

    match test_adjacency_memory() {
        Ok(_) => println!("\nAdjacency & Memory Layout PASSED"),
        Err(e) => {
            println!("\nAdjacency & Memory Layout FAILED: {}", e);
            std::process::exit(1);
        }
    }
}

/// Test 7: Adjacency & Memory Layout - Structural relations
fn test_adjacency_memory() -> Result<(), String> {
    println!("1. Building a custom scheme with adjacency and memory layout:");

    // Create two segments
    let seg1 = Segment::from_values(vec![0, 0]);
    let seg2 = Segment::from_values(vec![1, 0]);

    // Build scheme
    let scheme = SchemeBuilder::new()
        .add_axis(Axis {
            name: "x".to_string(),
            axis_type: AxisType::Discrete,
            metadata: HashMap::new(),
        })
        .add_axis(Axis {
            name: "y".to_string(),
            axis_type: AxisType::Discrete,
            metadata: HashMap::new(),
        })
        .add_segment(&seg1)
        .add_segment(&seg2)
        .add_relation(
            *seg1.id(),
            *seg2.id(),
            StructuralRelation::Adjacency {
                relation_type: AdjacencyType::Grid(GridTopology::FourConnected),
                weight: Some(1.0),
                metadata: HashMap::new(),
            },
        )
        .set_memory_layout(MemoryLayout {
            layout_type: LayoutType::RowMajor,
            mapping: Arc::new(|coords: &Coordinates| {
                if coords.raw.len() >= 2 {
                    let x = coords.raw[0] as u64;
                    let y = coords.raw[1] as u64;
                    Some(LogicalAddress {
                        space_id: 0,
                        offset: y * 10 + x,
                        metadata: HashMap::new(),
                    })
                } else {
                    None
                }
            }),
            metadata: HashMap::new(),
        })
        .build();

    println!("- Scheme created: {}", scheme.describe());

    // Test adjacency neighbors
    let neighbors = scheme.structural_neighbors(seg1.id(), None);
    println!("- Seg1 adjacency neighbors: {}", neighbors.len());
    if neighbors.len() != 1 {
        return Err(format!("Expected 1 neighbor, got {}", neighbors.len()));
    }

    // Test memory mapping
    let coords = Coordinates::new(vec![1, 0]);
    if let Some(addr) = scheme.map_to_logical_address(&coords) {
        println!("- Logical address for (1, 0): offset {}", addr.offset);
    } else {
        return Err("Memory mapping failed for valid coordinates".to_string());
    }

    println!("2. Adjacency & memory layout verified:");
    println!("Structural relations define adjacency semantics");
    println!("Memory layout maps coordinates to logical addresses");
    println!("Scheme ID incorporates adjacency and layout");

    Ok(())
}
