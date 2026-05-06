#!/usr/bin/env python3
"""
Generate LLM-friendly markdown documentation from Rust crates.

Single-file integration of the rustdoc JSON-to-Markdown converter with the
workspace/orchestration layer originally in doc.sh.  Runs cargo doc --no-deps
for each discovered workspace/crate in **parallel**, then converts the resulting
JSON output to Markdown (also in parallel), and finally generates llms.txt
(llmstxt.org) and index.md (Quarto-compatible).

Usage:
    python3 doc.py [--output-dir DIR] [--merge]

Examples:
    python3 doc.py
    python3 doc.py --output-dir ./target/llms-docs --merge

Note: --no-deps is ALWAYS enabled (hardcoded, matching doc.sh behavior).
"""

import argparse
import concurrent.futures
import glob
import json
import os
import re
import subprocess
import sys

# ===========================================================================
# Constants
# ===========================================================================
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "_llms")
IGNORE_DIRS = {"target", ".git", "node_modules"}
DOC_ARGS = "--no-deps"  # hardcoded, matching doc.sh line 143

# Rustdoc env for unstable JSON output
DOC_ENV = os.environ.copy()
DOC_ENV["RUSTC_BOOTSTRAP"] = "1"
DOC_ENV["RUSTDOCFLAGS"] = "-Z unstable-options --output-format json"

# Source file patterns to monitor for freshness
_SOURCE_PATTERNS = (".rs", "Cargo.toml", "Cargo.lock")


# ===========================================================================
# Utilities
# ===========================================================================
def resolve_abs(path: str) -> str:
    """Resolve a path to absolute, creating directories if needed."""
    p = os.path.abspath(path)
    os.makedirs(p, exist_ok=True)
    return p


def eprint(*args, **kwargs):
    """Print to stderr."""
    print(*args, file=sys.stderr, **kwargs)


# ===========================================================================
# Freshness check — avoid redundant cargo doc if JSON outputs are up-to-date
# ===========================================================================
def _latest_source_mtime(abs_dir: str) -> float:
    """Return the latest modification time of any tracked source file under abs_dir."""
    latest = 0.0
    for dirpath, dirnames, filenames in os.walk(abs_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            # str.endswith() accepts a tuple of suffixes natively
            if fn.endswith(_SOURCE_PATTERNS):
                fp = os.path.join(dirpath, fn)
                try:
                    mtime = os.path.getmtime(fp)
                    if mtime > latest:
                        latest = mtime
                except OSError:
                    continue
    return latest


def _is_docs_fresh(ws: dict) -> bool:
    """Check whether existing rustdoc JSON output is up-to-date vs source files.

    Returns True when *every* expected JSON file for the crate(s) in *ws*
    exists **and** has a modification time >= the newest source file mtime.
    This lets us skip the expensive ``cargo doc`` invocation entirely.

    For workspaces, we only check the explicitly listed member crates so that
    freshly-updated dependency JSONs (from a prior ``cargo doc``) do not
    accidentally make us think we are fresh when our own source changed.
    """
    abs_dir = ws["abs_dir"]
    crate_names = ws.get("crate_names", [])
    if not crate_names:
        return False

    json_dir = os.path.join(abs_dir, "target", "doc")
    expected_jsons = [os.path.join(json_dir, f"{name}.json") for name in crate_names]

    # Every expected file must exist
    for jp in expected_jsons:
        if not os.path.isfile(jp):
            return False

    # Latest source mtime
    src_mtime = _latest_source_mtime(abs_dir)
    if src_mtime == 0.0:
        return False  # no source files at all — treat as stale

    # Earliest JSON mtime among expected outputs
    try:
        json_mtime = min(os.path.getmtime(jp) for jp in expected_jsons)
    except OSError:
        return False

    return json_mtime >= src_mtime


# ===========================================================================
# Rustdoc JSON → Markdown Converter
# ===========================================================================
def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(data: dict, item_id: str) -> str:
    """Resolve the full Rust path for an item using the paths index."""
    paths = data.get("paths", {})
    if item_id in paths:
        segments = paths[item_id].get("path", [])
        return "::".join(segments)
    return ""


def get_simple_type(inner: dict) -> str:
    """Get the inner type key from an item's inner dict."""
    if not inner:
        return ""
    for k in (
        "module",
        "struct",
        "enum",
        "function",
        "trait",
        "impl",
        "variant",
        "struct_field",
        "use",
        "assoc_type",
        "static",
        "constant",
        "type_alias",
        "union",
        "foreign_type",
        "macro",
    ):
        if k in inner:
            return k
    return "unknown"


def format_docs(docs: str, indent: str = "") -> str:
    """Format doc comments as markdown text."""
    if not docs or not docs.strip():
        return ""
    lines = docs.strip().split("\n")
    result_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == "":
            result_lines.append("")
        else:
            result_lines.append(stripped)
    return "\n".join(result_lines)


def format_generics(generics: dict | None) -> str:
    """Format generic parameters and where clauses."""
    if not generics:
        return ""
    params = generics.get("params", [])
    where_preds = generics.get("where_predicates", [])
    parts = []
    for p in params:
        if isinstance(p, dict):
            name = p.get("name", "")
            kind = p.get("kind", {})
            if isinstance(kind, dict):
                if "type" in kind:
                    bounds = kind["type"].get("bounds", [])
                    if bounds:
                        bounds_str = ": " + " + ".join(_fmt_path(b) for b in bounds)
                        parts.append(f"{name}{bounds_str}")
                    else:
                        parts.append(name)
                elif "lifetime" in kind:
                    parts.append(f"'{name}")
                elif "const" in kind:
                    const_type = kind["const"].get("type", {})
                    parts.append(f"const {name}: {_fmt_path(const_type)}")
                else:
                    parts.append(name)
            else:
                parts.append(name)
    if not parts and not where_preds:
        return ""
    result = "<" + ", ".join(parts) + ">"
    if where_preds:
        where_str = " where " + ", ".join(_fmt_where_pred(w) for w in where_preds)
        result += where_str
    return result


def _fmt_path(p: dict | str | None) -> str:
    """Format a path-like structure to a string."""
    if p is None:
        return "_"
    if isinstance(p, str):
        return p
    if isinstance(p, dict):
        if "resolved_path" in p:
            rp = p["resolved_path"]
            path = rp.get("path", "")
            args = rp.get("args")
            if args:
                if isinstance(args, dict) and "angle_bracketed" in args:
                    ab = args["angle_bracketed"]
                    arg_list = ab.get("args", [])
                    formatted_args = []
                    for arg in arg_list:
                        if isinstance(arg, dict) and "type" in arg:
                            formatted_args.append(_fmt_path(arg["type"]))
                        else:
                            formatted_args.append(_fmt_path(arg))
                    return f"{path}<{', '.join(formatted_args)}>"
                elif isinstance(args, dict) and "parenthesized" in args:
                    pa = args["parenthesized"]
                    inputs = [_fmt_path(i.get("type", i)) for i in pa.get("inputs", [])]
                    output = _fmt_path(pa.get("output", {}))
                    return f"fn({', '.join(inputs)}) -> {output}"
            return path

        if "tuple" in p:
            elements = p["tuple"]
            if not elements:
                return "()"
            return f"({', '.join(_fmt_path(e) for e in elements)})"

        if "borrowed_ref" in p:
            br = p["borrowed_ref"]
            lifetime = br.get("lifetime", "")
            type_str = _fmt_path(br.get("type", {}))
            lifetime_str = f"'{lifetime} " if lifetime else ""
            return f"&{lifetime_str}{type_str}"

        if "raw_pointer" in p:
            rp = p["raw_pointer"]
            mut = "mut " if rp.get("mutability") == "mut" else "const "
            return f"*{mut}{_fmt_path(rp.get('type', {}))}"

        if "array" in p:
            arr = p["array"]
            return f"[{_fmt_path(arr.get('type', {}))}; {arr.get('len', '?')}]"
        if "slice" in p:
            return f"[{_fmt_path(p['slice'].get('type', {}))}]"

        if "path" in p:
            path_data = p["path"]
            if isinstance(path_data, str):
                return path_data
            if isinstance(path_data, dict):
                segments = path_data.get("data", {}).get("segments", [])
                parts = [s.get("name", "?") for s in segments]
                return "::".join(parts)
            if isinstance(path_data, list):
                return "::".join(str(s) for s in path_data)

        if "name" in p:
            return p["name"]
        if "primitive" in p:
            return p["primitive"]
        if "args" in p and p["args"]:
            return _fmt_path(p["args"])
        if "inferred" in p:
            return "_"
        if "never" in p:
            return "!"

    return str(p)


def _fmt_where_pred(w: dict) -> str:
    """Format a where predicate."""
    if isinstance(w, dict):
        bound_type = w.get("bound_type", {})
        if isinstance(bound_type, dict):
            bounds = bound_type.get("bounds", [])
            if bounds:
                t = _fmt_path(w.get("type", {}))
                b = _fmt_path(bounds[0])
                return f"{t}: {b}"
    return str(w)


def format_signature(item: dict) -> str:
    """Format the signature of a function item."""
    inner = item.get("inner", {})
    func = inner.get("function", {})
    sig = func.get("sig", {})

    name = item.get("name", "")

    decl_parts = []
    header = func.get("header", {})
    if header.get("const"):
        decl_parts.append("const")
    if header.get("async"):
        decl_parts.append("async")
    if header.get("unsafe"):
        decl_parts.append("unsafe")

    inputs = sig.get("input", []) if isinstance(sig, dict) else []
    output = sig.get("output", {}) if isinstance(sig, dict) else {}

    generics = func.get("generics", {})
    generic_str = format_generics(generics)

    is_method = sig.get("is_method", False) if isinstance(sig, dict) else False

    if is_method:
        self_arg = ""
        params = []
        for inp in inputs:
            if isinstance(inp, dict):
                pname = inp.get("name", "")
                ptype = _fmt_path(inp.get("type", {}))
                if pname in ("self", "mut self", "&self", "&mut self"):
                    self_arg = pname
                else:
                    params.append(f"{pname}: {ptype}" if pname else f"{ptype}")
        fn_sig = "fn "
        if self_arg:
            fn_sig += f"{name}{generic_str}({self_arg}"
            if params:
                fn_sig += ", " + ", ".join(params)
            fn_sig += ")"
        else:
            fn_sig += f"{name}{generic_str}(" + ", ".join(params) + ")"
    else:
        params = []
        for inp in inputs:
            if isinstance(inp, dict):
                pname = inp.get("name", "")
                ptype = _fmt_path(inp.get("type", {}))
                params.append(f"{pname}: {ptype}" if pname else f"{ptype}")
        fn_sig = f"fn {name}{generic_str}(" + ", ".join(params) + ")"

    if output and output != {}:
        out_str = _fmt_path(output)
        if out_str and out_str not in ("_", "()", ""):
            fn_sig += f" -> {out_str}"

    if decl_parts:
        result = " ".join(decl_parts) + " " + fn_sig
    else:
        result = fn_sig

    return f"```rust\n{result}\n```"


def format_struct_fields(item: dict, data: dict) -> str:
    """Format struct fields."""
    inner = item.get("inner", {})
    struct_inner = inner.get("struct", {})
    fields = struct_inner.get("fields", [])
    index_map = data.get("index", {})

    if not fields:
        return ""

    lines = []
    for field_id in fields:
        fid = str(field_id)
        fitem = index_map.get(fid, {})
        fname = fitem.get("name", "")
        fdocs = fitem.get("docs", "")
        finner = fitem.get("inner", {})
        ftype = ""
        if "struct_field" in finner:
            sf = finner["struct_field"]
            ftype = _fmt_path(sf.get("type", {}))

        if fname:
            lines.append(f"- **`{fname}`**`{': ' + ftype if ftype else ''}`")
        else:
            lines.append(f"- `{ftype}`")
        if fdocs and fdocs.strip():
            formatted = format_docs(fdocs)
            for fd_line in formatted.split("\n"):
                lines.append(f"  - {fd_line}")

    return "\n".join(lines)


def format_enum_variants(item: dict, data: dict) -> str:
    """Format enum variants."""
    inner = item.get("inner", {})
    enum_inner = inner.get("enum", {})
    variants = enum_inner.get("variants", [])
    index_map = data.get("index", {})

    if not variants:
        return ""

    lines = []
    for var_id in variants:
        vid = str(var_id)
        vitem = index_map.get(vid, {})
        vname = vitem.get("name", "")
        vdocs = vitem.get("docs", "")
        vinner = vitem.get("inner", {}).get("variant", {})
        vkind = vinner.get("kind", "") if isinstance(vinner, dict) else ""

        if vkind and vkind != "plain":
            lines.append(f"- **`{vname}`** `({vkind})`")
        else:
            lines.append(f"- **`{vname}`**")
        if vdocs and vdocs.strip():
            formatted = format_docs(vdocs)
            for vd_line in formatted.split("\n"):
                lines.append(f"  - {vd_line}")

    return "\n".join(lines)


def format_trait_items(item: dict, data: dict) -> str:
    """Format trait items."""
    inner = item.get("inner", {})
    trait_inner = inner.get("trait", {})
    trait_items = trait_inner.get("items", [])
    index_map = data.get("index", {})
    bounds = trait_inner.get("bounds", [])

    lines = []

    if bounds:
        bound_strs = []
        for b in bounds:
            if isinstance(b, dict):
                tb = b.get("trait_bound", b)
                trait_info = tb.get("trait", {})
                if isinstance(trait_info, dict):
                    path = trait_info.get("path", "")
                    if path:
                        bound_strs.append(path)
                    else:
                        bound_strs.append(_fmt_path(trait_info))
                else:
                    bound_strs.append(_fmt_path(tb))
        if bound_strs:
            lines.append(f"**Bounds:** `{', '.join(bound_strs)}`")
            lines.append("")

    if not trait_items:
        return "\n".join(lines)

    for titem_id in trait_items:
        tid = str(titem_id)
        titem = index_map.get(tid, {})
        tname = titem.get("name", "")
        tdocs = titem.get("docs", "")
        tinner_type = get_simple_type(titem.get("inner", {}))

        if tname:
            decl = f"  - `{tname}"
            if tinner_type == "function":
                sig = titem.get("inner", {}).get("function", {})
                gen = format_generics(sig.get("generics", {}))
                decl += gen
            decl += "`"
            lines.append(decl)
            if tdocs and tdocs.strip():
                formatted = format_docs(tdocs)
                for td_line in formatted.split("\n"):
                    lines.append(f"      {td_line}")

    return "\n".join(lines)


def collect_module_items(
    module_id: str, data: dict, depth: int = 0, max_depth: int = 10
) -> list:
    """Collect items from a module recursively, sorted by type then name."""
    index = data.get("index", {})
    item = index.get(module_id)
    if not item:
        return []

    inner = item.get("inner", {})
    module_inner = inner.get("module", {})
    child_ids = module_inner.get("items", [])

    collected = []
    for child_id in child_ids:
        cid = str(child_id)
        citem = index.get(cid)
        if not citem:
            continue

        inner_type = get_simple_type(citem.get("inner", {}))
        name = citem.get("name", "")

        # Skip impl blocks and use statements (noisy)
        if inner_type in ("impl", "use"):
            continue

        collected.append((cid, citem, inner_type, name, depth))

        # Recursively descend into submodules
        if inner_type == "module" and depth < max_depth:
            collected.extend(collect_module_items(cid, data, depth + 1, max_depth))

    return collected


def _sort_key(item_tuple):
    """Sort: modules first, then by type, then by name."""
    _, _, inner_type, name, depth = item_tuple
    type_order = {
        "module": 0,
        "trait": 1,
        "struct": 2,
        "enum": 3,
        "union": 4,
        "type_alias": 5,
        "function": 6,
        "constant": 7,
        "static": 8,
        "macro": 9,
        "assoc_type": 10,
    }
    order = type_order.get(inner_type, 99)
    return (depth, order, (name or "").lower())


def render_item(
    cid: str, citem: dict, inner_type: str, name: str, depth: int, data: dict
) -> str:
    """Render a single item as markdown."""
    docs = citem.get("docs", "")
    formatted_docs = format_docs(docs)
    heading_prefix = "#" * min(depth + 2, 6)
    lines = []

    if inner_type == "module":
        lines.append(f"{heading_prefix} Module `{name}`")
        if formatted_docs:
            lines.append("")
            lines.append(formatted_docs)
        return "\n".join(lines)

    full_path = resolve_path(data, cid)

    header = f"{heading_prefix} `{name}`"
    if full_path:
        header += f" *({full_path})*"
    lines.append(header)

    lines.append(f"*Type: {inner_type}*")
    lines.append("")

    if inner_type == "function":
        sig = format_signature(citem)
        lines.append(sig)
        lines.append("")
    elif inner_type == "struct":
        gen_str = format_generics(
            citem.get("inner", {}).get("struct", {}).get("generics", {})
        )
        decl = f"```rust\nstruct {name}{gen_str}\n```"
        lines.append(decl)
        lines.append("")
        fields_str = format_struct_fields(citem, data)
        if fields_str:
            lines.append("**Fields:**")
            lines.append("")
            lines.append(fields_str)
            lines.append("")
    elif inner_type == "enum":
        gen_str = format_generics(
            citem.get("inner", {}).get("enum", {}).get("generics", {})
        )
        decl = f"```rust\nenum {name}{gen_str}\n```"
        lines.append(decl)
        lines.append("")
        variants_str = format_enum_variants(citem, data)
        if variants_str:
            lines.append("**Variants:**")
            lines.append("")
            lines.append(variants_str)
            lines.append("")
    elif inner_type == "trait":
        gen_str = format_generics(
            citem.get("inner", {}).get("trait", {}).get("generics", {})
        )
        decl = f"```rust\ntrait {name}{gen_str}\n```"
        lines.append(decl)
        lines.append("")
        trait_items_str = format_trait_items(citem, data)
        if trait_items_str:
            lines.append("**Required Methods:**")
            lines.append("")
            lines.append(trait_items_str)
            lines.append("")
    elif inner_type == "type_alias":
        ta_inner = citem.get("inner", {}).get("type_alias", {})
        ta_type = _fmt_path(ta_inner.get("type", {}))
        lines.append(f"```rust\ntype {name} = {ta_type};\n```")
        lines.append("")
    elif inner_type == "constant":
        const_inner = citem.get("inner", {}).get("constant", {})
        const_type = _fmt_path(const_inner.get("type", {}))
        const_expr = const_inner.get("expr", "")
        lines.append(f"```rust\nconst {name}: {const_type} = {const_expr};\n```")
        lines.append("")
    elif inner_type == "static":
        static_inner = citem.get("inner", {}).get("static", {})
        static_type = _fmt_path(static_inner.get("type", {}))
        mutable = "mut " if static_inner.get("mutability") == "mut" else ""
        lines.append(f"```rust\nstatic {mutable}{name}: {static_type};\n```")
        lines.append("")
    elif inner_type == "macro":
        lines.append(f"```rust\nmacro_rules! {name} {{ ... }}\n```")
        lines.append("")

    if formatted_docs:
        lines.append(formatted_docs)
        lines.append("")

    return "\n".join(lines)


def convert(data: dict) -> str:
    """Convert rustdoc JSON data to markdown string."""
    index = data.get("index", {})
    root_id = str(data.get("root", ""))
    root_item = index.get(root_id, {})
    crate_name = root_item.get("name", data.get("target", "unknown"))
    crate_version = data.get("crate_version", "")

    lines = []

    title = f"# Crate `{crate_name}`"
    if crate_version:
        title += f" v{crate_version}"
    lines.append(title)
    lines.append("")

    root_docs = root_item.get("docs", "")
    if root_docs and root_docs.strip():
        lines.append(format_docs(root_docs))
        lines.append("")

    lines.append("---")
    lines.append("")

    all_items = collect_module_items(root_id, data)
    all_items.sort(key=_sort_key)

    emitted_modules = set()

    for cid, citem, inner_type, name, depth in all_items:
        if inner_type == "module":
            emitted_modules.add(cid)
            result = render_item(cid, citem, inner_type, name, depth, data)
            lines.append(result)
            lines.append("")
            lines.append("---")
            lines.append("")
        else:
            result = render_item(cid, citem, inner_type, name, depth, data)
            if result.strip():
                lines.append(result)
                lines.append("---")
                lines.append("")

    return "\n".join(lines)


def convert_file(json_path: str, output_path: str) -> bool:
    """Convert a single rustdoc JSON file to Markdown, writing to output_path.

    Returns True on success, False on failure.
    """
    if not os.path.exists(json_path):
        eprint(f"    Error: JSON file not found: {json_path}")
        return False

    try:
        data = load_json(json_path)
    except json.JSONDecodeError as e:
        eprint(f"    Error: Invalid JSON in {json_path}: {e}")
        return False

    markdown = convert(data)

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    return True


# ===========================================================================
# Discovery: workspaces and crate names
# ===========================================================================
def discover_crates(root_dir: str) -> list[dict]:
    """Discover Rust workspaces and standalone crates under root_dir.

    Returns a list of dicts with keys:
        - abs_dir: absolute path to the crate/workspace root
        - is_workspace: True if this is a workspace root
        - rel_dir: relative path for display
        - crate_names: list of package names (underscored) in this workspace/crate
    """
    cargo_tomls = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        if "Cargo.toml" in filenames:
            cargo_tomls.append(os.path.join(dirpath, "Cargo.toml"))

    workspaces: list[dict] = []
    standalone_candidates: list[dict] = []

    for cargo_path in cargo_tomls:
        abs_dir = os.path.abspath(os.path.dirname(cargo_path))
        rel_dir = os.path.relpath(abs_dir, root_dir)

        try:
            with open(cargo_path, "r", encoding="utf-8") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        has_workspace = re.search(r"^\[workspace\]", content, re.MULTILINE)
        has_package = re.search(r"^\[package\]", content, re.MULTILINE)

        crate_names: list[str] = []
        if has_package:
            m = re.search(r'^name\s*=\s*"([^"]+)"', content, re.MULTILINE)
            if m:
                crate_names.append(m.group(1).replace("-", "_"))

        entry = {
            "abs_dir": abs_dir,
            "rel_dir": rel_dir,
            "is_workspace": bool(has_workspace),
            "crate_names": crate_names,
        }

        if has_workspace:
            workspaces.append(entry)
        elif has_package:
            standalone_candidates.append(entry)

    # Filter out standalone crates that are workspace members
    ws_roots = {w["abs_dir"] for w in workspaces}

    for candidate in standalone_candidates:
        is_member = any(
            candidate["abs_dir"].startswith(ws_root + "/")
            or candidate["abs_dir"].startswith(ws_root + os.sep)
            for ws_root in ws_roots
        )
        if not is_member:
            workspaces.append(candidate)

    for ws in workspaces:
        if ws["is_workspace"]:
            ws_dir = ws["abs_dir"]
            member_names: list[str] = []
            for dirpath, dirnames, filenames in os.walk(ws_dir):
                dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
                if "Cargo.toml" in filenames:
                    try:
                        with open(
                            os.path.join(dirpath, "Cargo.toml"), "r", encoding="utf-8"
                        ) as f:
                            c = f.read()
                    except (OSError, UnicodeDecodeError):
                        continue
                    m = re.search(r'^name\s*=\s*"([^"]+)"', c, re.MULTILINE)
                    if m:
                        is_ws = re.search(r"^\[workspace\]", c, re.MULTILINE)
                        if not is_ws:
                            member_names.append(m.group(1).replace("-", "_"))
            ws["crate_names"] = member_names

    return workspaces


# ===========================================================================
# Parallel cargo doc + JSON→MD conversion
# ===========================================================================
def _run_cargo_doc_single(ws: dict) -> list[str]:
    """Run cargo doc --no-deps for a single workspace/crate.

    First checks whether existing rustdoc JSON output under ``target/doc/``
    is already fresh (newer than all source files).  If so, **skips** the
    ``cargo doc`` invocation entirely and returns the existing JSON paths
    directly — this avoids re-running rustdoc when the build artifacts from
    ``run.sh`` (or a prior doc generation) are still valid.

    Returns list of absolute paths to generated JSON files.
    Returns empty list on failure.
    """
    abs_dir = ws["abs_dir"]
    is_workspace = ws["is_workspace"]
    rel_dir = ws["rel_dir"]
    prefix = f"  [{rel_dir}]"

    # ------------------------------------------------------------------
    # Freshness check — avoid redundant cargo doc when JSON outputs exist
    # and are newer than all tracked source files.
    # ------------------------------------------------------------------
    if _is_docs_fresh(ws):
        json_dir = os.path.join(abs_dir, "target", "doc")
        json_files = sorted(glob.glob(os.path.join(json_dir, "*.json")))
        if json_files:
            crate_list = ws.get("crate_names", [])
            print(
                f"{prefix} rustdoc JSON is fresh ({len(crate_list)} crate(s)) — skipping cargo doc"
            )
            return json_files
        # Fall-through: glob returned nothing despite _is_docs_fresh saying
        # every expected file exists.  Should not happen, but be defensive.

    cmd = ["cargo", "doc"]
    cmd.extend(DOC_ARGS.split())
    if is_workspace:
        cmd.append("--workspace")

    try:
        result = subprocess.run(
            cmd,
            cwd=abs_dir,
            env=DOC_ENV,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            eprint(f"{prefix} cargo doc failed. stderr (first 500 chars):")
            for line in result.stderr.strip().split("\n")[:20]:
                eprint(f"  | {line}")
            return []
    except subprocess.TimeoutExpired:
        eprint(f"{prefix} Timed out (600s). Skipping.")
        return []
    except FileNotFoundError:
        eprint(f"{prefix} ERROR: cargo not found. Is Rust installed?")
        raise  # fatal — let main() handle it

    json_dir = os.path.join(abs_dir, "target", "doc")
    if not os.path.isdir(json_dir):
        print(f"{prefix} No JSON output directory found.")
        return []

    json_files = sorted(glob.glob(os.path.join(json_dir, "*.json")))
    if not json_files:
        print(f"{prefix} No JSON files found.")
        return []

    return json_files


def _convert_single_json(
    json_file: str, output_dir: str, known_names: set[str], ws_prefix: str = ""
) -> str | None:
    """Convert a single JSON file to Markdown, returning the output path or None.

    When *ws_prefix* is non-empty (e.g. ``"standard/crates/core"``), the
    output filename is prefixed with the sanitised workspace path so that
    crates with identical names in different workspaces do not collide::

        {sanitised_prefix}-{crate_name}.md

    The separator ``-`` was chosen because the project's crate names use
    underscores (``_``), making it unambiguous to strip the prefix later.
    """
    crate_name = os.path.splitext(os.path.basename(json_file))[0]

    if crate_name not in known_names:
        return None  # skip dependency

    if ws_prefix:
        safe_prefix = ws_prefix.strip("/").replace("/", "_")
        out_md = os.path.join(output_dir, f"{safe_prefix}-{crate_name}.md")
    else:
        out_md = os.path.join(output_dir, f"{crate_name}.md")

    if convert_file(json_file, out_md):
        return out_md
    return None


def generate_docs_parallel(
    workspaces: list[dict],
    output_dir: str,
    max_workers: int | None = None,
) -> tuple[list[str], set[str]]:
    """Run cargo doc + JSON→MD conversion for all workspaces in parallel.

    Phase 1 — cargo doc for all workspaces simultaneously.
    Phase 2 — JSON→MD conversion for all discovered JSON files simultaneously.

    Returns:
        generated_files: list of generated markdown file paths.
        known_crate_names: set of all known project crate names (underscored).
    """
    all_known_names: set[str] = set()
    for ws in workspaces:
        all_known_names.update(ws.get("crate_names", []))

    print()
    print(" Generating LLM-friendly markdown documentation...")

    # Clean output directory (skip files starting with uppercase letter)
    for existing in glob.glob(os.path.join(output_dir, "*.md")):
        basename = os.path.basename(existing)
        if basename and basename[0].isupper():
            # Keep files like README.md, LICENSE.md, etc.
            continue
        os.remove(existing)

    # ------------------------------------------------------------------
    # Phase 1: Parallel cargo doc
    # ------------------------------------------------------------------
    print()
    print(
        f" Phase 1: Running cargo doc for {len(workspaces)} workspace(s) in parallel..."
    )
    print()

    all_json_files: list[str] = []
    json_file_to_ws: dict[str, str] = {}  # json path → workspace rel_dir
    worker_count = max_workers or min(len(workspaces), os.cpu_count() or 4)

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(_run_cargo_doc_single, ws): ws for ws in workspaces
        }
        for future in concurrent.futures.as_completed(future_map):
            ws = future_map[future]
            try:
                json_files = future.result()
            except FileNotFoundError:
                eprint("  cargo not found. Install Rust: https://rustup.rs")
                sys.exit(1)

            if json_files:
                for jf in json_files:
                    json_file_to_ws[jf] = ws["rel_dir"]
                all_json_files.extend(json_files)
                print(f"  ✓ [{ws['rel_dir']}] generated {len(json_files)} JSON file(s)")
            else:
                print(f"  - [{ws['rel_dir']}] no JSON output")

    if not all_json_files:
        print("  No JSON files generated from any workspace.")
        return [], all_known_names

    print()
    print(f" complete: {len(all_json_files)} JSON file(s) total.")

    # ------------------------------------------------------------------
    # Phase 2: Parallel JSON → MD conversion
    # ------------------------------------------------------------------
    print()
    print(
        f" Phase 2: Converting {len(all_json_files)} JSON file(s) to Markdown in parallel..."
    )
    print()

    generated_files: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_map = {
            executor.submit(
                _convert_single_json,
                jf,
                output_dir,
                all_known_names,
                json_file_to_ws.get(jf, ""),
            ): jf
            for jf in all_json_files
        }
        for future in concurrent.futures.as_completed(future_map):
            json_file = future_map[future]
            try:
                result = future.result()
            except Exception as e:
                eprint(f"  Error converting {os.path.basename(json_file)}: {e}")
                continue

            if result:
                generated_files.append(result)
                print(f"  ✓ {os.path.basename(result)}")
            else:
                crate_name = os.path.splitext(os.path.basename(json_file))[0]
                if crate_name not in all_known_names:
                    pass  # silently skip deps
                else:
                    print(f"  ✗ conversion failed for {json_file}")

    generated_files.sort()
    return generated_files, all_known_names


# ===========================================================================
# Merge
# ===========================================================================
def merge_markdown_files(generated_files: list[str], output_path: str):
    """Merge all generated markdown files into a single file."""
    print()
    print(f" Merging all markdown files into {output_path}...")

    with open(output_path, "w", encoding="utf-8") as merged:
        for md_file in generated_files:
            if not os.path.isfile(md_file):
                continue
            merged.write(f"<!-- {md_file} -->\n")
            with open(md_file, "r", encoding="utf-8") as f:
                merged.write(f.read())
            merged.write("\n\n")

    print(f" Merged document: {output_path}")


# ===========================================================================
# Helper: extract the crate-name suffix from a potentially prefixed filename
# ===========================================================================
def _crate_basename_stem(bn: str) -> str:
    """Return the crate-name portion of a (possibly workspace-prefixed) markdown filename.

    Crate names in this project use only underscores (``_``), and the
    workspace prefix is separated from the crate name by ``-``.  This
    function splits on the **last** ``-`` (safe because crate names do
    not contain hyphens) and returns the part after it.

    Examples::

        "standard_crates_core-ssccs_core.md"    → "ssccs_core"
        "baremetal_riscv-ssccs_baremetal_riscv.md" → "ssccs_baremetal_riscv"
        "ssccs_core.md"                         → "ssccs_core"

    When there is no prefix (no ``-`` before ``.md``), the entire stem
    is returned.
    """
    stem = bn[:-3] if bn.endswith(".md") else bn
    parts = stem.rsplit("-", 1)
    return parts[-1]


# ===========================================================================
# llms.txt (llmstxt.org standard)
# ===========================================================================
def extract_title(md_file: str) -> str:
    """Extract H1 title from a markdown file, stripping '# ' prefix and version suffix."""
    try:
        with open(md_file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
    except (OSError, UnicodeDecodeError):
        return os.path.splitext(os.path.basename(md_file))[0]

    title = re.sub(r"^#\s+", "", first_line)
    title = re.sub(r"\s+v[0-9][0-9.]*$", "", title)
    return title


def generate_llms_txt(
    output_dir: str, generated_files: list[str], merged: bool, merged_path: str | None
):
    """Generate llms.txt following the llmstxt.org standard."""
    llms_txt = os.path.join(output_dir, "llms.txt")
    print()
    print(" Generating llms.txt (llmstxt.org standard)...")

    core_files = []
    exp_files = []
    bm_files = []

    skip_basenames = {"llms.txt", "llms-full.txt", "index.qmd", "index.md"}

    for f in generated_files:
        if not os.path.isfile(f):
            continue
        bn = os.path.basename(f)
        if bn in skip_basenames:
            continue
        stem = _crate_basename_stem(bn)
        if stem.startswith("ssccs_baremetal_") or stem.startswith("crate_"):
            bm_files.append(f)
        elif stem.startswith("ssccs_"):
            core_files.append(f)
        elif stem.startswith("experiment_"):
            exp_files.append(f)

    with open(llms_txt, "w", encoding="utf-8") as out:
        out.write("# SSCSS Documentation\n")
        out.write("\n")
        out.write(
            "> SSCSS (Scheme-Centric Computation on Silicon Substrates) is a Rust framework "
            "providing core abstractions for scheme-based computation, with hardware integration "
            "targets including RISC-V.\n"
        )
        out.write("\n")
        out.write("\n")

        if core_files:
            out.write("## Core Crates\n")
            out.write("\n")
            for f in sorted(core_files):
                bn = os.path.basename(f)
                title = extract_title(f)
                out.write(f"- [{title}]({bn})\n")
            out.write("\n")

        if exp_files:
            out.write("## Experiments\n")
            out.write("\n")
            for f in sorted(exp_files):
                bn = os.path.basename(f)
                title = extract_title(f)
                out.write(f"- [{title}]({bn})\n")
            out.write("\n")

        if bm_files:
            out.write("## Baremetal / Platform\n")
            out.write("\n")
            for f in sorted(bm_files):
                bn = os.path.basename(f)
                title = extract_title(f)
                out.write(f"- [{title}]({bn})\n")
            out.write("\n")

        out.write("## Optional\n")
        out.write("\n")

        if merged and merged_path and os.path.isfile(merged_path):
            out.write(
                "- [Merged full documentation](llms-full.txt): Consolidated single-file documentation for LLM context\n"
            )

        out.write("\n")

    print(f" Generated: {llms_txt}")


# ===========================================================================
# index.md (Quarto-compatible)
# ===========================================================================
def generate_index_md(
    output_dir: str, generated_files: list[str], merged: bool, merged_path: str | None
):
    """Generate index.md (Quarto-compatible) with collection links."""
    index_md = os.path.join(output_dir, "index.md")
    print()
    print(" Generating index.md with collection links...")

    core_files = []
    exp_files = []
    bm_files = []

    skip_basenames = {"llms.txt", "llms-full.txt", "index.qmd", "index.md"}

    for f in generated_files:
        if not os.path.isfile(f):
            continue
        bn = os.path.basename(f)
        if bn in skip_basenames:
            continue
        stem = _crate_basename_stem(bn)
        if stem.startswith("ssccs_baremetal_") or stem.startswith("crate_"):
            bm_files.append(f)
        elif stem.startswith("ssccs_"):
            core_files.append(f)
        elif stem.startswith("experiment_"):
            exp_files.append(f)

    with open(index_md, "w", encoding="utf-8") as out:
        out.write("---\n")
        out.write('title: "SSCSS Documentation Index"\n')
        out.write("format: html\n")
        out.write("toc: true\n")
        out.write("---\n")
        out.write("\n")
        out.write(
            "This index provides an overview of all documented Rust crates in the SSCSS project.\n"
        )
        out.write("\n")
        out.write(
            "For LLM-friendly consumption, see [llms.txt](llms.txt) following the [llmstxt.org](https://llmstxt.org/) standard.\n"
        )
        out.write("\n")

        if core_files:
            out.write("## Core Crates\n")
            out.write("\n")
            out.write("| Crate | Documentation |\n")
            out.write("|-------|---------------|\n")
            for f in sorted(core_files):
                bn = os.path.basename(f)
                title = extract_title(f)
                out.write(f"| {title} | [browse]({bn}) |\n")
            out.write("\n")

        if exp_files:
            out.write("## Experiments\n")
            out.write("\n")
            out.write("| Experiment | Documentation |\n")
            out.write("|------------|---------------|\n")
            for f in sorted(exp_files):
                bn = os.path.basename(f)
                title = extract_title(f)
                out.write(f"| {title} | [browse]({bn}) |\n")
            out.write("\n")

        if bm_files:
            out.write("## Baremetal / Platform\n")
            out.write("\n")
            out.write("| Crate | Documentation |\n")
            out.write("|-------|---------------|\n")
            for f in sorted(bm_files):
                bn = os.path.basename(f)
                title = extract_title(f)
                out.write(f"| {title} | [browse]({bn}) |\n")
            out.write("\n")

        if merged and merged_path and os.path.isfile(merged_path):
            out.write("## Merged LLM Document\n")
            out.write("\n")
            out.write(
                "The entire documentation has been consolidated into a single file: [llms-full.txt](llms-full.txt)\n"
            )
            out.write("\n")

    print(f" Generated: {index_md}")


# ===========================================================================
# Main entry point
# ===========================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Generate LLM-friendly markdown documentation from Rust crates."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for generated docs (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge all generated markdown files into a single file (llms-full.txt)",
    )
    parser.add_argument(
        "--no-deps",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=None,
        help="Number of parallel workers (default: min(workspaces, cpu_count))",
    )
    args = parser.parse_args()

    output_dir = resolve_abs(args.output_dir)

    # ── Step 1: Discover ──
    print(" Discovering Rust workspaces and crates...")
    root_dir = os.path.abspath(".")
    workspaces = discover_crates(root_dir)

    if not workspaces:
        print(" No Rust workspaces or crates found.")
        sys.exit(1)

    print(f" Found {len(workspaces)} workspace(s).")
    for ws in workspaces:
        tag = "workspace" if ws["is_workspace"] else "standalone"
        print(f"   - {ws['rel_dir']} ({tag}, {len(ws['crate_names'])} crate(s))")

    # ── Step 2: Parallel cargo doc + conversion ──
    generated_files, known_names = generate_docs_parallel(
        workspaces,
        output_dir,
        max_workers=args.jobs,
    )

    if not generated_files:
        print(" No markdown files were generated.")
        sys.exit(1)

    # ── Step 3: Merge ──
    merged_path: str | None = None
    if args.merge:
        merged_path = os.path.join(output_dir, "llms-full.txt")
        merge_markdown_files(generated_files, merged_path)

    # ── Step 4: llms.txt ──
    generate_llms_txt(output_dir, generated_files, args.merge, merged_path)

    # ── Step 5: index.md ──
    generate_index_md(output_dir, generated_files, args.merge, merged_path)

    # ── Done ──
    print()
    print("=" * 57)
    print("  Documentation generation complete!")
    print("=" * 57)
    print()
    print(f" Output directory: {output_dir}")
    print(f" Generated {len(generated_files)} markdown files.")
    if args.merge and merged_path:
        print(f" Merged file: {merged_path}")
    print(f" llms.txt (llmstxt.org): {os.path.join(output_dir, 'llms.txt')}")
    print(f" Index (Quarto): {os.path.join(output_dir, 'index.md')}")
    print()


if __name__ == "__main__":
    main()
