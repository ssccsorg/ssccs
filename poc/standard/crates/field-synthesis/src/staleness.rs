//! Composite versions: a composition over fields that change.
//!
//! The whitepaper gives a composite its own version, a hash of its constituents' versions and the operation, and
//! asks for the structure to be rebuilt when an observation finds that version changed rather than after every
//! update. A `ComposedField` holds snapshots, so without that rule a constituent's update would go unseen.
//!
//! Nothing here reads a clock or polls a field. A composite answers two questions: what version it is at, and
//! whether the structure it holds answers that version.

use std::fmt::Debug;
use std::sync::{Arc, Mutex};

use ssccs_core::{Coordinates, EvolvingField, Field};

use crate::{ComposedExpr, ComposedField, CompositionOp};

/// A constituent a composite can read: its version, and a snapshot of what it enforces now.
///
/// `snapshot` returns the pair because a rebuild records the version beside the structure it built from that
/// snapshot. Reading them separately would let an update land in between and stamp a new version on old contents.
/// The snapshot is what makes a rebuild atomic in the other direction too: no evaluation ever sees half an update.
pub trait VersionedField: Debug + Send + Sync {
    fn version(&self) -> u64;
    fn snapshot(&self) -> (u64, Field);
}

impl VersionedField for EvolvingField {
    fn version(&self) -> u64 {
        EvolvingField::version(self)
    }

    fn snapshot(&self) -> (u64, Field) {
        (self.version(), self.field().clone())
    }
}

/// A field that changes between two observations is shared, so the shared form is the one a composite reads.
/// One lock covers both values, which is what keeps the pair consistent for a caller on another thread.
impl VersionedField for Mutex<EvolvingField> {
    fn version(&self) -> u64 {
        match self.lock() {
            Ok(field) => field.version(),
            Err(poisoned) => poisoned.into_inner().version(),
        }
    }

    fn snapshot(&self) -> (u64, Field) {
        let field = match self.lock() {
            Ok(field) => field,
            Err(poisoned) => poisoned.into_inner(),
        };
        (field.version(), field.field().clone())
    }
}

/// The version of a composite, as the appendix states it: a hash of the parts' versions and the operation.
///
/// Position carries a constituent's identity, so `union(a, b)` and `union(b, a)` differ. A different operation over
/// the same parts differs likewise, which is what stops a union and an intersection from sharing a cached result.
pub fn composite_version(op: CompositionOp, parts: &[u64]) -> u64 {
    let mut hasher = blake3::Hasher::new();
    hasher.update(&[match op {
        CompositionOp::Union => 0,
        CompositionOp::Intersection => 1,
        CompositionOp::Product => 2,
    }]);
    for version in parts {
        hasher.update(&version.to_le_bytes());
    }

    let digest = hasher.finalize();
    let mut bytes = [0u8; 8];
    bytes.copy_from_slice(&digest.as_bytes()[..8]);
    u64::from_le_bytes(bytes)
}

/// A composite of two versioned fields, holding a structure built at one version.
///
/// `allows` takes `&mut self` because the rebuild happens inside the observation, which is where the appendix puts
/// it. A composite asked the same version twice builds nothing the second time, and `rebuilds` counts the builds so
/// the laziness is a number rather than a claim.
#[derive(Debug)]
pub struct LazyComposite {
    op: CompositionOp,
    left: Arc<dyn VersionedField>,
    right: Arc<dyn VersionedField>,
    left_axes: Option<usize>,
    built: ComposedField,
    built_version: u64,
    rebuilds: u64,
}

impl LazyComposite {
    pub fn new(
        op: CompositionOp,
        left: Arc<dyn VersionedField>,
        right: Arc<dyn VersionedField>,
    ) -> Self {
        let (built, built_version) = build(op, None, &left, &right);
        Self {
            op,
            left,
            right,
            left_axes: None,
            built,
            built_version,
            rebuilds: 0,
        }
    }

    /// Partition the axes, which `CompositionOp::Product` requires.
    ///
    /// This composes again without counting a rebuild: the count is for version-driven rebuilds, and a builder call
    /// is not one.
    pub fn with_left_axes(mut self, axes: usize) -> Self {
        let (built, built_version) = build(self.op, Some(axes), &self.left, &self.right);
        self.left_axes = Some(axes);
        self.built = built;
        self.built_version = built_version;
        self
    }

    /// The composite version of the constituents as they stand.
    pub fn version(&self) -> u64 {
        composite_version(self.op, &[self.left.version(), self.right.version()])
    }

    /// How many times the structure has been rebuilt since it was first composed.
    pub fn rebuilds(&self) -> u64 {
        self.rebuilds
    }

    /// Whether the structure held answers the constituents as they stand.
    pub fn is_current(&self) -> bool {
        self.built_version == self.version()
    }

    /// The structure, rebuilt first if the version moved since it was built.
    pub fn structure(&mut self) -> &ComposedField {
        if !self.is_current() {
            self.rebuild();
        }
        &self.built
    }

    pub fn allows(&mut self, coords: &Coordinates) -> bool {
        self.structure().allows(coords)
    }

    pub fn describe(&mut self) -> String {
        self.structure().describe()
    }

    fn rebuild(&mut self) {
        let (built, built_version) = build(self.op, self.left_axes, &self.left, &self.right);
        self.built = built;
        self.built_version = built_version;
        self.rebuilds += 1;
    }
}

/// The structure for the constituents as they stand, and the version that describes exactly that pair.
///
/// The two constituents are read one after the other, so the pair is not a simultaneous reading of both. Each half
/// is consistent with the version recorded for it, which is the strongest claim available without a lock shared by
/// every constituent.
fn build(
    op: CompositionOp,
    left_axes: Option<usize>,
    left: &Arc<dyn VersionedField>,
    right: &Arc<dyn VersionedField>,
) -> (ComposedField, u64) {
    let (left_version, left_field) = left.snapshot();
    let (right_version, right_field) = right.snapshot();

    let composed = ComposedField::new(
        ComposedExpr::from(left_field),
        ComposedExpr::from(right_field),
        op,
    );
    let composed = match left_axes {
        Some(axes) => composed.with_left_axes(axes),
        None => composed,
    };

    let version = composite_version(op, &[left_version, right_version]);
    (composed, version)
}
