//! Writes a Scheme's address decoder, and the table the decoder is swept against.
//!
//! `make -C sv generate` runs this with `--out`, and `make -C sv decode-check` sweeps the module in simulation. The
//! table comes from the Scheme's own segments rather than from the emitter's arithmetic, so the sweep compares two
//! derivations of the same space instead of one derivation against itself.
//!
//! The demo space is a four by three grid, written here rather than taken from a template so that the binary does
//! not depend on the template crate.

use std::path::{Path, PathBuf};
use std::process::ExitCode;

use ssccs_core::{ConstraintSpec, Segment, eval_constraint};
use ssccs_hardware_mapping::{AxisExtent, address_of, axis_extents, emit_address_decode_sv};
use ssccs_primitive::{Axis, AxisType, Scheme, SchemeBuilder};

const MODULE: &str = "ssccs_address_decode";
const LINE_MODULE: &str = "ssccs_line_decode";

fn axis(name: &str) -> Axis {
    Axis {
        name: name.to_string(),
        axis_type: AxisType::Discrete,
        metadata: Default::default(),
    }
}

fn demo() -> Scheme {
    let mut builder = SchemeBuilder::new().add_axis(axis("x")).add_axis(axis("y"));
    for x in 0..4i64 {
        for y in 0..3i64 {
            builder = builder.add_segment(&Segment::from_values(vec![x, y]));
        }
    }
    builder.build()
}

/// The space the board sweeps: a line of sixteen points three apart, so the address is not the coordinate.
fn line() -> Scheme {
    let mut builder = SchemeBuilder::new().add_axis(axis("value"));
    for value in (0..=45i64).step_by(3) {
        builder = builder.add_segment(&Segment::from_value(value));
    }
    builder.build()
}

/// The program the board's observation module carries: `even and range [0, 10]`.
fn board_program() -> Vec<ConstraintSpec> {
    vec![
        ConstraintSpec::Even,
        ConstraintSpec::Range { min: 0, max: 10 },
    ]
}

/// The points of `scheme` the program admits, which is what the die's count is compared against.
fn admissions(scheme: &Scheme, program: &[ConstraintSpec]) -> u64 {
    scheme
        .segments()
        .filter(|segment| {
            segment
                .coordinates()
                .raw
                .first()
                .is_some_and(|value| program.iter().all(|spec| eval_constraint(spec, *value)))
        })
        .count() as u64
}

fn main() -> ExitCode {
    let mut out: Option<PathBuf> = None;

    let mut args = std::env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "--out" => match args.next() {
                Some(dir) => out = Some(PathBuf::from(dir)),
                None => {
                    eprintln!("usage: emit-decode [--out DIR]");
                    return ExitCode::from(2);
                }
            },
            _ => {
                eprintln!("usage: emit-decode [--out DIR]");
                return ExitCode::from(2);
            }
        }
    }

    let scheme = demo();
    let extents = match axis_extents(&scheme) {
        Ok(extents) => extents,
        Err(error) => {
            eprintln!("emit-decode: the Scheme has no arithmetic map: {error}");
            return ExitCode::from(1);
        }
    };
    let total: u64 = extents.iter().map(|extent| extent.size).product();

    let sv = match emit_address_decode_sv(MODULE, &scheme) {
        Ok(sv) => sv,
        Err(error) => {
            eprintln!("emit-decode: {error}");
            return ExitCode::from(1);
        }
    };

    let line_scheme = line();
    let line_total: u64 = line_scheme.segments().count() as u64;
    let line_admissions = admissions(&line_scheme, &board_program());

    println!("=== Address decode ===");
    println!();
    println!("  module:    {MODULE}");
    println!("  axes:      {}", extents.len());
    for extent in &extents {
        println!(
            "    {}: {} values from {}, step {}",
            extent.name, extent.size, extent.offset, extent.rate
        );
    }
    println!("  addresses: {total}");
    println!("  size:      {} bytes", sv.len());
    println!();
    println!(
        "  board:     {LINE_MODULE} over a strided line, {} admissions of {}",
        line_admissions, line_total
    );

    let Some(dir) = out else {
        return ExitCode::SUCCESS;
    };

    if let Err(error) = write(&dir, &sv, &scheme, &extents, line_total, line_admissions) {
        eprintln!("emit-decode: {error}");
        return ExitCode::from(1);
    }
    println!();
    println!("  wrote {}", dir.display());
    ExitCode::SUCCESS
}

fn write(
    dir: &Path,
    sv: &str,
    scheme: &Scheme,
    extents: &[AxisExtent],
    line_total: u64,
    line_admissions: u64,
) -> std::io::Result<()> {
    std::fs::create_dir_all(dir)?;
    std::fs::write(dir.join(format!("{MODULE}.sv")), sv)?;

    let total: u64 = extents.iter().map(|extent| extent.size).product();
    let mut table = vec![vec![0i64; total as usize]; extents.len()];

    for segment in scheme.segments() {
        let index = address_of(extents, segment.coordinates())
            .ok_or_else(|| std::io::Error::other("a segment has no address"))?;
        for (axis, value) in segment.coordinates().raw.iter().enumerate() {
            table[axis][index as usize] = *value;
        }
    }

    for (axis, values) in table.iter().enumerate() {
        let rows: String = values
            .iter()
            .map(|value| format!("{:016X}\n", *value as u64))
            .collect();
        std::fs::write(dir.join(format!("address_coord{axis}.hex")), rows)?;
    }

    let board = line();
    let board_sv = emit_address_decode_sv(LINE_MODULE, &board).map_err(std::io::Error::other)?;
    std::fs::write(dir.join(format!("{LINE_MODULE}.sv")), board_sv)?;

    // The space the sweep covers, then the count the die compares against and one off it for the control.
    std::fs::write(dir.join("decode_space.hex"), format!("{line_total:016X}\n"))?;
    std::fs::write(
        dir.join("decode_count.hex"),
        format!("{line_admissions:016X}\n"),
    )?;
    std::fs::write(
        dir.join("decode_count_off.hex"),
        format!("{:016X}\n", line_admissions + 1),
    )?;

    Ok(())
}
