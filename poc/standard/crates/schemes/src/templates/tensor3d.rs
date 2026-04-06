//! 3D Tensor Scheme Template

use ssccs_core::Segment;
use ssccs_primitive::scheme::abstract_scheme::{
    AdjacencyType, Axis, AxisType, Scheme, SchemeBuilder, StructuralRelation,
};
use std::collections::HashMap;

/// 3D Tensor Scheme Template
pub struct Tensor3DTemplate {
    width: i64,
    height: i64,
    depth: i64,
    adjacency_type: AdjacencyType,
}

impl Tensor3DTemplate {
    pub fn new(width: i64, height: i64, depth: i64) -> Self {
        Self {
            width,
            height,
            depth,
            adjacency_type: AdjacencyType::Manhattan(1),
        }
    }

    pub fn build(self) -> Scheme {
        let mut builder = SchemeBuilder::new()
            .add_axis(Axis {
                name: "x".to_string(),
                axis_type: AxisType::Discrete,
                metadata: [
                    ("range_start".to_string(), "0".to_string()),
                    ("range_end".to_string(), self.width.to_string()),
                ]
                .iter()
                .cloned()
                .collect(),
            })
            .add_axis(Axis {
                name: "y".to_string(),
                axis_type: AxisType::Discrete,
                metadata: [
                    ("range_start".to_string(), "0".to_string()),
                    ("range_end".to_string(), self.height.to_string()),
                ]
                .iter()
                .cloned()
                .collect(),
            })
            .add_axis(Axis {
                name: "z".to_string(),
                axis_type: AxisType::Discrete,
                metadata: [
                    ("range_start".to_string(), "0".to_string()),
                    ("range_end".to_string(), self.depth.to_string()),
                ]
                .iter()
                .cloned()
                .collect(),
            });

        // Segment creation
        let mut segments = Vec::new();
        let mut coord_to_id = HashMap::new();
        for x in 0..self.width {
            for y in 0..self.height {
                for z in 0..self.depth {
                    let segment = Segment::from_values(vec![x, y, z]);
                    coord_to_id.insert((x, y, z), *segment.id());
                    segments.push(segment);
                }
            }
        }
        builder = builder.add_segments(segments.clone());

        // Add adjacency relationships (6-connected Manhattan distance 1)
        for x in 0..self.width {
            for y in 0..self.height {
                for z in 0..self.depth {
                    let from_id = coord_to_id[&(x, y, z)];
                    // neighbor offsets
                    let offsets = vec![
                        (-1, 0, 0),
                        (1, 0, 0),
                        (0, -1, 0),
                        (0, 1, 0),
                        (0, 0, -1),
                        (0, 0, 1),
                    ];
                    for (dx, dy, dz) in offsets {
                        let nx = x + dx;
                        let ny = y + dy;
                        let nz = z + dz;
                        if nx >= 0
                            && nx < self.width
                            && ny >= 0
                            && ny < self.height
                            && nz >= 0
                            && nz < self.depth
                        {
                            if let Some(&to_id) = coord_to_id.get(&(nx, ny, nz)) {
                                builder = builder.add_relation(
                                    from_id,
                                    to_id,
                                    StructuralRelation::Adjacency {
                                        relation_type: self.adjacency_type.clone(),
                                        weight: Some(1.0),
                                        metadata: HashMap::new(),
                                    },
                                );
                            }
                        }
                    }
                }
            }
        }

        builder = builder.add_metadata("template".to_string(), "tensor3d".to_string());

        builder.build()
    }
}
