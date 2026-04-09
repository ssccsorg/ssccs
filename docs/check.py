#!/usr/bin/env python3
import os
import re
from pathlib import Path

def get_std_base(name: str) -> str:
    """
    Standardizes a filename while preserving Quarto's partial file prefix (_).
    Example: "_License-Page.qmd" -> "_license_page"
    """
    base = os.path.splitext(name)[0]
    if base.upper() == "README":
        return "README"
    
    # Check if it starts with an underscore (Quarto partials/includes)
    prefix = "_" if base.startswith("_") else ""
    actual_base = base[1:] if base.startswith("_") else base
    
    # Clean string: lower, swap spaces/dashes to underscores
    new_base = actual_base.lower().replace(" ", "_").replace("-", "_")
    # Remove non-alphanumeric chars (preserving underscores)
    new_base = re.sub(r'[^a-z0-9_\u1100-\u11FF\uAC00-\uD7AF]', '', new_base)
    # Collapse multiple underscores
    new_base = re.sub(r'_+', '_', new_base).strip('_')
    
    return prefix + new_base

def build_global_inventory(root_path: Path) -> dict:
    """
    Scans the entire directory to map standardized keys to actual file paths.
    """
    inventory = {}
    ignored_dirs = {'.venv', '.git', '_site', '.quarto', 'node_modules'}
    
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ignored_dirs and not d.startswith('.')]
        
        for f in files:
            if f.endswith(('.md', '.qmd', '.html')):
                std_key = get_std_base(f)
                full_path = Path(root) / f
                # Store the relative path from the project root
                inventory[std_key] = full_path.relative_to(root_path)
                
    return inventory

def sync_all_links(target_dir: str):
    root = Path(target_dir).resolve()
    if not root.exists():
        print(f"ERROR: Target directory not found: {root}")
        return

    # STEP 1: Global Indexing
    print(f" Global Indexing: Scanning all files in {root}...")
    inventory = build_global_inventory(root)
    print(f" Indexed {len(inventory)} unique documents.")
    print("-" * 60)

    # STEP 2: Pattern Definition
    # Matches /path/to/file.ext, ./file.ext, ../file.ext, etc.
    link_pattern = re.compile(
        r'/?(?:\.{1,2}/)*[\w\-\.]+(?:/[\w\-\.]+)*\.(?:md|qmd|html)',
        re.IGNORECASE
    )

    total_fixed = 0
    processed_files = 0
    target_extensions = {'.md', '.qmd', '.yml', '.json', '.html'}

    for current_root, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in {'.venv', '.git', '_site'}]
        
        for fname in files:
            file_path = Path(current_root) / fname
            if file_path.suffix not in target_extensions:
                continue

            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
            except Exception as e:
                print(f"Could not read {fname}: {e}")
                continue

            processed_files += 1

            def replacer(match):
                nonlocal total_fixed
                orig_link = match.group(0)
                
                # --- PROTECTION LOGIC ---
                # Check context around the match to avoid Quarto shortcodes/includes
                start_index = match.start()
                # Check 15 characters before the match for "include" or "{{<"
                buffer_before = content[max(0, start_index-20):start_index]
                if "include" in buffer_before or "{{" in buffer_before:
                    return orig_link # Skip modification for includes
                
                # Separate path from possible anchor (#) or query (?)
                base_url = orig_link.split('#')[0].split('?')[0]
                extra = orig_link[len(base_url):]
                
                filename = os.path.basename(base_url)
                std_key = get_std_base(filename)

                if std_key in inventory:
                    target_file = inventory[std_key]
                    
                    # Logic: If original link used .html, maintain .html for production
                    # Otherwise, use the actual source extension found in inventory
                    orig_ext = os.path.splitext(filename)[1].lower()
                    new_ext = ".html" if orig_ext == ".html" else target_file.suffix
                    
                    # Reconstruct file name from actual target
                    new_filename = get_std_base(target_file.name) + new_ext
                    
                    # Replace only the filename part to preserve directory structure (/docs/...)
                    dir_part = os.path.dirname(base_url)
                    # Use forward slashes for URLs regardless of OS
                    new_base_url = os.path.join(dir_part, new_filename).replace(os.sep, '/')
                    
                    if new_base_url != base_url:
                        total_fixed += 1
                        return new_base_url + extra
                
                return orig_link

            new_content = link_pattern.sub(replacer, content)
            
            if content != new_content:
                file_path.write_text(new_content, encoding='utf-8')
                print(f" Fixed links in: {file_path.relative_to(root)}")

    print("-" * 60)
    print(f" Processed {processed_files} files.")
    print(f" Total links synchronized: {total_fixed}")

if __name__ == "__main__":
    sync_all_links("./")