use std::env;
use std::fs;
use std::path::Path;

fn main() {
    let asm_path = Path::new("asm/observe_full.S");
    println!("cargo:rerun-if-changed={}", asm_path.display());
    let content = fs::read_to_string(asm_path).expect("can't read observe_full.S");
    let out = env::var("OUT_DIR").unwrap();
    let out_path = Path::new(&out).join("asm_data.rs");
    let mut data = String::from("// Auto-generated from observe_full.S by build.rs\n");
    data.push_str("#[allow(dead_code)]\npub mod asm_data {\n");
    let mut n = 0u32;
    for line in content.lines() {
        let t = line.trim();
        let Some(col) = t.find(':') else { continue };
        let bef = &t[..col];
        let sym = bef
            .strip_prefix(".globl ")
            .map(|g| g.split(';').next().unwrap_or(g))
            .unwrap_or(bef)
            .trim()
            .split_whitespace()
            .last()
            .unwrap_or("");
        if sym.is_empty() || sym.starts_with('#') || sym.starts_with('.') {
            continue;
        }
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
        n += 1;
        if nums.len() == 1 {
            data.push_str(&format!("    pub const {}: i64 = {};\n", sym, nums[0]));
        } else {
            let s = nums
                .iter()
                .map(|v| v.to_string())
                .collect::<Vec<_>>()
                .join(", ");
            data.push_str(&format!(
                "    pub const {}: [i64; {}] = [{}];\n",
                sym,
                nums.len(),
                s
            ));
        }
    }
    data.push_str("}\n");
    fs::write(&out_path, data).expect("write failed");
    println!("cargo:note=asm_data: {} constants from .S", n);
}
