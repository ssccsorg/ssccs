use std::env;
use std::fs;
use std::path::Path;

/// Parse a single assembly file and return its module name and a list of constant declarations.
fn parse_asm_file(path: &Path) -> (String, Vec<String>) {
    let content = fs::read_to_string(path).unwrap_or_else(|_| panic!("can't read {:?}", path));
    let stem = path.file_stem().unwrap().to_str().unwrap().to_string();
    let mut consts = Vec::new();

    for line in content.lines() {
        let t = line.trim();

        // Find a line with a colon (label definition)
        let Some(col) = t.find(':') else { continue };
        let bef = &t[..col];

        // Extract symbol name from `.globl sym` or bare label
        let sym = bef
            .strip_prefix(".globl ")
            .map(|g| g.split(';').next().unwrap_or(g))
            .unwrap_or(bef)
            .split_whitespace()
            .last()
            .unwrap_or("");
        if sym.is_empty() || sym.starts_with('#') || sym.starts_with('.') {
            continue;
        }

        // Find .8byte data directive
        let Some(dp) = t.find(".8byte") else { continue };
        let nums: Vec<i64> = t[dp + 7..]
            .split('#')
            .next()
            .unwrap_or("")
            .split(',')
            .filter_map(|s| s.trim().parse().ok())
            .collect();
        if nums.is_empty() {
            continue;
        }

        let decl = if nums.len() == 1 {
            format!("    pub const {}: i64 = {};", sym, nums[0])
        } else {
            let vals = nums
                .iter()
                .map(i64::to_string)
                .collect::<Vec<_>>()
                .join(", ");
            format!("    pub const {}: [i64; {}] = [{}];", sym, nums.len(), vals)
        };
        consts.push(decl);
    }

    (stem, consts)
}

fn main() {
    let asm_dir = Path::new("asm");
    if !asm_dir.is_dir() {
        panic!("asm/ directory not found");
    }

    let out = env::var("OUT_DIR").unwrap();
    let out_path = Path::new(&out).join("asm_data.rs");

    // Discover all .S files in asm/
    let mut entries: Vec<_> = fs::read_dir(asm_dir)
        .expect("can't read asm/")
        .filter_map(|e| e.ok())
        .filter(|e| e.path().extension().map(|x| x == "S").unwrap_or(false))
        .map(|e| e.path())
        .collect();
    entries.sort();

    let mut data = String::from("// Auto-generated from asm/*.S by build.rs\n");
    data.push_str("#[allow(dead_code)]\npub mod asm_data {\n");

    let mut total = 0u32;
    for path in &entries {
        let (stem, consts) = parse_asm_file(path);
        println!("cargo:rerun-if-changed={}", path.display());

        if consts.is_empty() {
            continue;
        }

        data.push_str(&format!("    pub mod {} {{\n", stem));
        for c in &consts {
            data.push_str(&format!("{}\n", c));
        }
        data.push_str("    }\n");
        total += consts.len() as u32;
    }

    data.push_str("}\n");
    fs::write(&out_path, data).expect("write failed");
    println!(
        "cargo:note=asm_data: {} constants from {} file(s)",
        total,
        entries.len()
    );
}
