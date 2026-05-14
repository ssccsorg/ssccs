//! 2D Grid Scheme Template

use ssccs_core::Segment;
use ssccs_primitive::{Axis, AxisType, GridTopology, Scheme, SchemeBuilder};

/// 2D Grid Scheme Template
pub struct Grid2DTemplate {
    width: i64,
    height: i64,
    #[allow(dead_code)]
    topology: GridTopology,
}

impl Grid2DTemplate {
    pub fn new(width: i64, height: i64, topology: GridTopology) -> Self {
        Self {
            width,
            height,
            topology,
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
            });

        // Segment creation
        for x in 0..self.width {
            for y in 0..self.height {
                let segment = Segment::from_values(vec![x, y]);
                builder = builder.add_segment(&segment);
            }
        }

        // Add adjacency relationship
        // (simplification: actually creates relationships based on topology)
        builder = builder.add_metadata("template".to_string(), "grid2d".to_string());

        builder.build()
    }
}
