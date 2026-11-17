# Field evolution

The whitepaper's appendix `sec-appendix-dynamic-field-evolution` specifies how a Field stops being a fixed
admissible set. This entry states which part of that specification the POC implements, how the log decides, and
what the POC leaves to a caller.

## The model

`ssccs_core::EvolvingField` holds a `Field`, a list of rules, an append-only log and a version. The log is the whole
input. Nothing in the module reads a clock, spawns work or consults outside state, so the same log produces the same
evolution, and a run is reproducible by replaying it.

An entry is one of five things: the field's creation, an external event, an observation, another field's update, or
this field's own applied update. A rule is a trigger over those entries and an update.

An update restates the constraints rather than mutating state: `Set` replaces the set, `Add` extends it, and an
empty `Set` admits the whole space. The version counts restatements, so a projection computed against one version
stays meaningful until the next one.

## The triggers

| Trigger | Fires on |
|---|---|
| `After { delta }` | the entry whose time is at least `delta` past the last applied update |
| `OnEvent { id }` | the external event with that identifier |
| `ProjectionAbove { threshold }` | an observation whose projection is above the threshold |
| `OnUpdateOf { field }` | another field's update, by name |
| `All`, `Any`, `Sequence` | the constituents, over the history for `All`, at the entry for `Any`, in order for `Sequence` |

Two decisions are worth stating because the appendix does not spell them out.

The clock `After` reads is the time of the last update the field applied, not the time of the last entry. A stream
of events therefore does not starve or accelerate a temporal rule, and an update re-arms the trigger it came from.
`All` asks whether each constituent has happened at or before the entry, since a conjunction of two distinct events
never holds at a single entry; it fires on the entry that completes the set and does not rise again until a
constituent falls and returns. `Any` asks whether the entry satisfies a constituent, so a periodic constituent keeps
firing and an event constituent fires per occurrence.

One call applies at most one update per rule, in declaration order, so a chain of rules cannot loop inside a call.
The caller drives the next cycle, which is what makes convergence a property of the log rather than of a scheduler.

## Determinism

`deterministic` is a property of the triggers. Time is a coordinate the caller writes, so a temporal trigger is
deterministic. An external event originates outside the model, so a trigger that waits for one is not, and the
conjunction, disjunction or sequence containing one is not either.

## Evidence

`crates/core/tests/evolution.rs` pins the appendix's `temperature_alarm` example and one case per composite form,
including the clock's re-arming and the fact that a rule fires once per entry. `crates/concepts/src/bin/concept-evolution.rs`
prints the same example as a trace of versions and admissible sets, and `run.sh` builds and runs it with the other
concepts.

## What the POC does not implement

The cache. The appendix calls versioned projection caching an optimisation and not mandatory, so the POC states
the version and leaves storage to a caller.

Composite staleness, whose version is a hash of the constituent versions and the operation. That belongs where
composition lives, `ssccs-field-synthesis`, and it is a separate change.

A runtime event loop, a timer queue and a `max_updates` policy. The caller supplies entries and decides when to
stop, which is what keeps the evaluation deterministic and testable.

The open-format `triggers` block, which the appendix marks as a future schema version.

One limitation is deliberate: an update's spec applies to the axis the `EvolvingField` was constructed with, because
a constraint spec names a kind and a bound while the axis is the field's choice. A Field whose several axes evolve
independently gets one `EvolvingField` per axis.
