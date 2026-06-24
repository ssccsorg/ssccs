//! Reporter capability — formats observation results for output.
//!
//! Follows the same capability-trait pattern as ev's ReporterCapable.
//! Each output format (text, JSON, CSV) implements the SsccsReporter trait.

use crate::ObservationResult;
use ssccs_core::Projector;

/// Capability: format and output observation results.
pub trait SsccsReporter<P: Projector> {
    /// Report observation results. Returns true if all observations passed.
    fn report(&self, target: &str, scheme_desc: &str, result: &ObservationResult<P>) -> bool;
}

/// Text reporter — human-readable pass/fail per segment.
pub struct TextReport;

impl<P: Projector> SsccsReporter<P> for TextReport
where
    P::Output: std::fmt::Display,
{
    fn report(&self, target: &str, _scheme_desc: &str, result: &ObservationResult<P>) -> bool {
        println!("target: {}", target);
        println!("total:  {}", result.total);
        println!("passed: {}", result.admitted);
        println!("failed: {}", result.rejected);
        if result.rejected > 0 {
            for (sid, obs) in &result.results {
                if obs.is_none() {
                    println!("  [FAIL] {} — {}", hex::encode(sid.as_bytes()), result.field_desc);
                }
            }
        }
        if result.admitted == result.total {
            println!();
            println!("All combinations passed.");
        }
        result.rejected == 0
    }
}

/// JSON reporter — structured output for CI and machine consumption.
pub struct JsonReport;

impl<P: Projector> SsccsReporter<P> for JsonReport
where
    P::Output: serde::Serialize,
{
    fn report(&self, target: &str, _scheme_desc: &str, result: &ObservationResult<P>) -> bool {
        let payload = serde_json::json!({
            "target": target,
            "total": result.total,
            "passed": result.admitted,
            "failed": result.rejected,
            "field_constraints": result.field_desc,
        });
        println!("{}", serde_json::to_string_pretty(&payload).unwrap());
        result.rejected == 0
    }
}

/// CSV reporter — flat table for analysis.
pub struct CsvReport;

impl<P: Projector> SsccsReporter<P> for CsvReport
where
    P::Output: std::fmt::Display,
{
    fn report(&self, target: &str, _scheme_desc: &str, result: &ObservationResult<P>) -> bool {
        println!("# target: {}", target);
        println!("# total: {}, passed: {}, failed: {}", result.total, result.admitted, result.rejected);
        println!("segment_id,passed,projection");
        for (sid, obs) in &result.results {
            let proj = match obs {
                Some(v) => format!("{}", v),
                None => "REJECT".into(),
            };
            println!("{},{}", hex::encode(sid.as_bytes()), proj);
        }
        result.rejected == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use ssccs_core::{Coordinates, Field, Projector, Segment, segment_id_from_coords};
    use std::collections::HashMap;

    /// A simple projector for testing.
    #[derive(Debug, Clone)]
    struct TestProjector;

    impl Projector for TestProjector {
        type Output = i64;

        fn project(&self, _field: &Field, segment: &Segment) -> Option<Self::Output> {
            Some(segment.coordinates().get_axis(0).unwrap_or(0))
        }

        fn possible_next_coordinates(&self, _coords: &Coordinates) -> Vec<Coordinates> {
            Vec::new()
        }
    }

    fn make_result(total: usize, admitted: usize) -> ObservationResult<TestProjector> {
        let mut results = Vec::new();
        for i in 0..total {
            let coords = Coordinates::new(vec![i as i64]);
            let segment = Segment::new(coords);
            let obs = if i < admitted { Some(i as i64) } else { None };
            results.push((*segment.id(), obs));
        }
        ObservationResult {
            total,
            admitted,
            rejected: total - admitted,
            results,
            field_desc: "no constraints".into(),
            scheme_desc: "test".into(),
            target: "test_target".into(),
        }
    }

    #[test]
    fn text_report_all_pass() {
        let result = make_result(10, 10);
        let reporter = TextReport;
        assert!(reporter.report("test", "", &result));
    }

    #[test]
    fn text_report_with_failures() {
        let result = make_result(10, 7);
        let reporter = TextReport;
        assert!(!reporter.report("test", "", &result));
    }

    #[test]
    fn json_report_all_pass() {
        let result = make_result(10, 10);
        let reporter = JsonReport;
        assert!(reporter.report("test", "", &result));
    }

    #[test]
    fn json_report_with_failures() {
        let result = make_result(10, 3);
        let reporter = JsonReport;
        assert!(!reporter.report("test", "", &result));
    }

    #[test]
    fn csv_report_output() {
        let result = make_result(5, 3);
        let reporter = CsvReport;
        assert!(!reporter.report("test", "", &result));
    }
}
