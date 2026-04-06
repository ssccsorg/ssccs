//! Graph-based Scheme Template

use ssccs_core::Segment;
use ssccs_primitive::{AdjacencyType, Axis, AxisType, Scheme, SchemeBuilder, StructuralRelation};
use std::collections::HashMap;

/// Graph-based Scheme Template
pub struct GraphTemplate {
    nodes: Vec<Vec<i64>>,            // node coordinates
    edges: Vec<(usize, usize, f64)>, // (from_idx, to_idx, weight)
}

impl GraphTemplate {
    pub fn new(nodes: Vec<Vec<i64>>, edges: Vec<(usize, usize, f64)>) -> Self {
        Self { nodes, edges }
    }

    pub fn build(self) -> Scheme {
        let mut builder = SchemeBuilder::new();

        // Dimension axis (variable length)
        for i in 0..self.nodes[0].len() {
            builder = builder.add_axis(Axis {
                name: format!("dim_{}", i),
                axis_type: AxisType::Discrete,
                metadata: HashMap::new(),
            });
        }

        // Create node segments
        let segments: Vec<Segment> = self
            .nodes
            .iter()
            .map(|coords| Segment::from_values(coords.clone()))
            .collect();

        builder = builder.add_segments(segments.clone());

        // Add edge relationships
        for (from_idx, to_idx, weight) in self.edges {
            if let (Some(from_seg), Some(to_seg)) = (segments.get(from_idx), segments.get(to_idx)) {
                builder = builder.add_relation(
                    *from_seg.id(),
                    *to_seg.id(),
                    StructuralRelation::Adjacency {
                        relation_type: AdjacencyType::Graph,
                        weight: Some(weight),
                        metadata: [("edge_type".to_string(), "directed".to_string())]
                            .iter()
                            .cloned()
                            .collect(),
                    },
                );
            }
        }

        builder = builder.add_metadata("template".to_string(), "graph".to_string());

        builder.build()
    }
}
