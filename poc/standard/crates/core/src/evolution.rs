//! Field evolution: triggers, versions, and the log they read.
//!
//! The whitepaper models a trigger as a predicate over an append-only log rather than as a scheduler, so this
//! module owns a log and evaluates rules against it. A caller supplies every entry: the field's creation, an
//! external event, an observation, another field's update. Nothing here reads a clock and nothing here spawns work,
//! which is what makes the same log produce the same evolution.
//!
//! An update restates what the field enforces, so an evolution is a sequence of admissible sets rather than a
//! mutation of state. The version counts those restatements, and a projection computed against one version stays
//! valid until the next one.

use crate::core::{Coordinates, Field};
use crate::spec::ConstraintSpec;
use crate::{EvenConstraint, GtConstraint, RangeConstraint};

/// One entry in a field's append-only log.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FieldLogEntry {
    /// The field was created at this time, and no update has been applied yet.
    Created { at: i64 },
    /// An external event arrived.
    Event { at: i64, id: String },
    /// An observation produced this projection.
    Observed { at: i64, projection: i64 },
    /// Another field completed an update, reaching this version.
    Updated {
        at: i64,
        field: String,
        version: u64,
    },
    /// This field applied the rule at this index.
    Applied { at: i64, rule: usize },
}

impl FieldLogEntry {
    /// The time axis at this entry.
    pub fn at(&self) -> i64 {
        match self {
            FieldLogEntry::Created { at }
            | FieldLogEntry::Event { at, .. }
            | FieldLogEntry::Observed { at, .. }
            | FieldLogEntry::Updated { at, .. }
            | FieldLogEntry::Applied { at, .. } => *at,
        }
    }
}

/// What a fired rule does to the field's constraint set.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ConstraintUpdate {
    /// Replace the constraints with these. An empty list admits the whole space.
    Set(Vec<ConstraintSpec>),
    /// Add these to whatever the field already carries.
    Add(Vec<ConstraintSpec>),
}

/// A trigger, as a predicate over the log.
///
/// `All` reads the history and `Any` reads the entry, which is what the whitepaper's wording implies: AND fires
/// when all constituents have fired, OR fires when one does. A field-level conjunction of two distinct events
/// would never hold at a single entry, so `All` asks whether each has happened at or before this one and fires on
/// the entry that completes the set.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum FieldTrigger {
    /// Fires once the time axis has advanced by `delta` since the previous update.
    After { delta: i64 },
    /// Fires on the external event with this identifier.
    OnEvent { id: String },
    /// Fires on an observation whose projection is above the threshold.
    ProjectionAbove { threshold: i64 },
    /// Fires when the named field completes an update.
    OnUpdateOf { field: String },
    /// Fires when every constituent has fired.
    All(Vec<FieldTrigger>),
    /// Fires when a constituent fires.
    Any(Vec<FieldTrigger>),
    /// Fires when the constituents fire in this order, each after the one before it.
    ///
    /// A later occurrence of the last part fires again once a prefix exists, which is what makes a sequence over a
    /// recurring event recurring.
    Sequence(Vec<FieldTrigger>),
}

impl FieldTrigger {
    /// Whether the trigger can be evaluated from the log alone.
    ///
    /// Time is a coordinate the caller writes into the log, so a temporal trigger is deterministic. An external
    /// event originates outside the model, which is why a trigger that waits for one is not.
    pub fn deterministic(&self) -> bool {
        match self {
            FieldTrigger::OnEvent { .. } => false,
            FieldTrigger::All(inner) | FieldTrigger::Any(inner) | FieldTrigger::Sequence(inner) => {
                inner.iter().all(FieldTrigger::deterministic)
            }
            FieldTrigger::After { .. }
            | FieldTrigger::ProjectionAbove { .. }
            | FieldTrigger::OnUpdateOf { .. } => true,
        }
    }

    fn holds_at(&self, log: &[FieldLogEntry], index: usize) -> bool {
        match self {
            FieldTrigger::After { delta } => match previous_update(log, index) {
                Some(last) => log[index].at() - last >= *delta,
                None => false,
            },
            FieldTrigger::OnEvent { id } => {
                matches!(&log[index], FieldLogEntry::Event { id: other, .. } if other == id)
            }
            FieldTrigger::ProjectionAbove { threshold } => {
                matches!(&log[index], FieldLogEntry::Observed { projection, .. } if *projection > *threshold)
            }
            FieldTrigger::OnUpdateOf { field } => {
                matches!(&log[index], FieldLogEntry::Updated { field: other, .. } if other == field)
            }
            FieldTrigger::All(inner) => {
                !inner.is_empty()
                    && inner.iter().all(|t| held_at_or_before(t, log, index))
                    && (index == 0 || !inner.iter().all(|t| held_at_or_before(t, log, index - 1)))
            }
            FieldTrigger::Any(inner) => inner.iter().any(|t| t.holds_at(log, index)),
            FieldTrigger::Sequence(inner) => match inner.split_last() {
                Some((last, init)) => {
                    last.holds_at(log, index) && in_order_before(init, log, index)
                }
                None => false,
            },
        }
    }
}

/// A trigger and the update it applies.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EvolutionRule {
    pub trigger: FieldTrigger,
    pub update: ConstraintUpdate,
}

impl EvolutionRule {
    pub fn new(trigger: FieldTrigger, update: ConstraintUpdate) -> Self {
        Self { trigger, update }
    }
}

/// What one log entry did.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct UpdateReport {
    /// The rules that fired, in declaration order.
    pub fired: Vec<usize>,
    /// The field's version after the entry.
    pub version: u64,
}

impl UpdateReport {
    pub fn fired_any(&self) -> bool {
        !self.fired.is_empty()
    }
}

/// A Field whose constraint set its own log decides.
///
/// `axis` is the axis an update's spec applies to, because a constraint spec names a kind and a bound and the axis
/// is the field's choice. A field with more than one evolving axis gets one of these per axis.
#[derive(Debug)]
pub struct EvolvingField {
    field: Field,
    axis: usize,
    rules: Vec<EvolutionRule>,
    log: Vec<FieldLogEntry>,
    version: u64,
}

impl EvolvingField {
    /// Start an evolution at `created_at`, which is the time a temporal trigger measures from before its first
    /// update.
    pub fn new(field: Field, axis: usize, created_at: i64) -> Self {
        Self {
            field,
            axis,
            rules: Vec::new(),
            log: vec![FieldLogEntry::Created { at: created_at }],
            version: 0,
        }
    }

    pub fn add_rule(&mut self, rule: EvolutionRule) {
        self.rules.push(rule);
    }

    /// The number of updates applied, which starts at zero.
    pub fn version(&self) -> u64 {
        self.version
    }

    pub fn log(&self) -> &[FieldLogEntry] {
        &self.log
    }

    pub fn field(&self) -> &Field {
        &self.field
    }

    /// Whether every rule can be evaluated from the log alone.
    pub fn deterministic(&self) -> bool {
        self.rules.iter().all(|rule| rule.trigger.deterministic())
    }

    pub fn allows(&self, coords: &Coordinates) -> bool {
        self.field.allows(coords)
    }

    /// Append one entry and apply what it triggers.
    ///
    /// Each rule is evaluated once against the history before the entry, in declaration order, so one call applies
    /// at most one update per rule and a chain of updates cannot loop inside a call. An update this call applies is
    /// appended after the entry, so it cannot change how a later rule reads the history. The clock a temporal
    /// trigger reads is the time of the most recent applied update, so an update re-arms the trigger it came from,
    /// and a caller that keeps the condition true gets one update per `delta` rather than one per entry.
    pub fn record(&mut self, entry: FieldLogEntry) -> UpdateReport {
        self.log.push(entry);
        let index = self.log.len() - 1;
        let at = self.log[index].at();

        let firing: Vec<usize> = (0..self.rules.len())
            .filter(|rule| self.rules[*rule].trigger.holds_at(&self.log, index))
            .collect();

        let mut fired = Vec::with_capacity(firing.len());
        for rule in firing {
            let update = self.rules[rule].update.clone();
            self.apply(update);
            self.version += 1;
            self.log.push(FieldLogEntry::Applied { at, rule });
            fired.push(rule);
        }

        UpdateReport {
            fired,
            version: self.version,
        }
    }

    fn apply(&mut self, update: ConstraintUpdate) {
        match update {
            ConstraintUpdate::Set(specs) => {
                self.field.clear_constraints();
                self.add_constraints(&specs);
            }
            ConstraintUpdate::Add(specs) => self.add_constraints(&specs),
        }
    }

    fn add_constraints(&mut self, specs: &[ConstraintSpec]) {
        let axis = self.axis;
        for spec in specs {
            match spec {
                ConstraintSpec::Even => self.field.add_constraint(EvenConstraint::new(axis)),
                ConstraintSpec::Range { min, max } => self
                    .field
                    .add_constraint(RangeConstraint::new(axis, *min, *max)),
                // An equality is a range with one point, which is why the substrate has no separate unit for it.
                ConstraintSpec::Eq { value } => self
                    .field
                    .add_constraint(RangeConstraint::new(axis, *value, *value)),
                ConstraintSpec::Gt { value } => {
                    self.field.add_constraint(GtConstraint::new(axis, *value))
                }
            }
        }
    }
}

/// The time of the most recent update before `before`, which is the creation time while none has been applied.
fn previous_update(log: &[FieldLogEntry], before: usize) -> Option<i64> {
    log[..before].iter().rev().find_map(|entry| match entry {
        FieldLogEntry::Applied { at, .. } | FieldLogEntry::Created { at } => Some(*at),
        _ => None,
    })
}

/// Whether `trigger` holds at any entry up to and including `upto`.
fn held_at_or_before(trigger: &FieldTrigger, log: &[FieldLogEntry], upto: usize) -> bool {
    (0..=upto).any(|index| trigger.holds_at(log, index))
}

/// Whether the parts each hold somewhere before `before`, in the order given.
fn in_order_before(parts: &[FieldTrigger], log: &[FieldLogEntry], before: usize) -> bool {
    let mut next = 0;
    for index in 0..before {
        if next < parts.len() && parts[next].holds_at(log, index) {
            next += 1;
        }
    }
    next == parts.len()
}
