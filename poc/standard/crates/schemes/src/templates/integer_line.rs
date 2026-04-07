//! 1D Linear Scheme Template (Integer Arithmetic)

use ssccs_core::Segment;
use ssccs_primitive::{Axis, AxisType, Scheme, SchemeBuilder};

/// 1D Integer Line Scheme Template
pub struct IntegerLineTemplate {
    start: i64,
    end: i64,
    step: i64,
}

impl IntegerLineTemplate {
    pub fn new(start: i64, end: i64, step: i64) -> Self {
        Self { start, end, step }
    }

    pub fn build(self) -> Scheme {
        let mut builder = SchemeBuilder::new().add_axis(Axis {
            name: "value".to_string(),
            axis_type: AxisType::Discrete,
            metadata: [
                ("range_start".to_string(), self.start.to_string()),
                ("range_end".to_string(), self.end.to_string()),
                ("step".to_string(), self.step.to_string()),
            ]
            .iter()
            .cloned()
            .collect(),
        });

        // Segment creation
        let mut value = self.start;
        while value <= self.end {
            let segment = Segment::from_value(value);
            builder = builder.add_segment(segment);
            value += self.step;
        }

        // Adjacency relationship (linear)
        // (simplification: actually just adding neighbor relationships)

        builder = builder.add_metadata("template".to_string(), "integer_line".to_string());

        builder.build()
    }
}
