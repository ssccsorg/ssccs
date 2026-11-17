//! Writes the observation modules the anchor scenario pins, for the elaboration and simulation gates.
//!
//! `make -C sv generate` runs this with `--out`, and `make -C sv check` then simulates the result against the golden
//! anchors and elaborates it. With no arguments the binary reports the programs and writes nothing, which keeps the
//! workspace-wide run of every binary quiet.
//!
//! The two programs carry the same constraints and differ only in the join, so the emitted pair says what the
//! composition operator does to an admissible set: `even and [0, 10]` admits 2 and 10, `even or [0, 10]` admits
//! every coordinate the anchors carry.

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use ssccs_core::ConstraintSpec;
use ssccs_hardware_mapping::{ComposeOp, ConstraintProgram, ProjectorUnit, emit_observation_sv};

/// One constraint set, joined twice.
fn constraints() -> Vec<ConstraintSpec> {
    vec![
        ConstraintSpec::Even,
        ConstraintSpec::Range { min: 0, max: 10 },
    ]
}

fn programs() -> Vec<(&'static str, ConstraintProgram)> {
    vec![
        (
            "ssccs_generated_narrow",
            ConstraintProgram {
                constraints: constraints(),
                compose: ComposeOp::And,
            },
        ),
        (
            "ssccs_generated_broad",
            ConstraintProgram {
                constraints: constraints(),
                compose: ComposeOp::Or,
            },
        ),
    ]
}

fn usage() -> ExitCode {
    eprintln!("usage: emit-observation [--out DIR] [--print]");
    ExitCode::from(2)
}

fn main() -> ExitCode {
    let mut out: Option<PathBuf> = None;
    let mut print = false;

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--out" => match args.next() {
                Some(dir) => out = Some(PathBuf::from(dir)),
                None => return usage(),
            },
            "--print" => print = true,
            _ => return usage(),
        }
    }

    let mut emitted = Vec::new();
    for (name, program) in programs() {
        let sv = emit_observation_sv(name, &program, ProjectorUnit::Identity);
        emitted.push((name, program, sv));
    }

    println!("=== Observation modules ===");
    println!();
    for (name, program, sv) in &emitted {
        println!("  {name}");
        println!("    admissible set: {}", program.describe());
        println!(
            "    projection:     {}",
            ProjectorUnit::Identity.module_name()
        );
        println!("    size:           {} bytes", sv.len());
        if print {
            println!();
            print!("{sv}");
        }
    }

    if let Some(dir) = out {
        for (name, _, sv) in &emitted {
            if let Err(error) = write(&dir, name, sv) {
                eprintln!("emit-observation: {error}");
                return ExitCode::from(1);
            }
            println!();
            println!("  wrote {}", dir.join(format!("{name}.sv")).display());
        }
    }

    ExitCode::SUCCESS
}

fn write(dir: &Path, name: &str, sv: &str) -> std::io::Result<()> {
    std::fs::create_dir_all(dir)?;
    std::fs::write(dir.join(format!("{name}.sv")), sv)
}
