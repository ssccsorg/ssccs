"""
Create a standalone C2PA manifest for a PDF file using c2patool's built-in test certificate.

Derived from docs/_utils/sign_c2pa.py.
"""

import json
import hashlib
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def calculate_sha256(file_path: Path) -> str:
    """Calculate the SHA-256 hex digest of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def create_metadata_file(path: Path, pdf_hash: str, manifest_json_path: Path) -> None:
    """
    Create an SVG file that contains:
    - a custom attribute pdf:hash with the PDF hash,
    - the full original manifest JSON embedded inside <metadata> as CDATA.
    """
    with open(manifest_json_path, "r", encoding="utf-8") as f:
        manifest_str = f.read()

    svg_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<svg xmlns="http://www.w3.org/2000/svg"\n'
        '     xmlns:pdf="https://ssccs.org/ns/pdfhash"\n'
        f'     pdf:hash="sha256:{pdf_hash}">\n'
        "  <metadata>\n"
        "    <![CDATA[\n"
        f"{manifest_str}\n"
        "    ]]>\n"
        "  </metadata>\n"
        "</svg>\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg_content)


def sign_pdf(
    pdf_path: Path,
    manifest_path: Path,
    output_path: Path,
    c2patool: str | None = None,
) -> bool:
    """
    Apply a C2PA signature to a PDF using c2patool with its built-in test
    certificate.

    Parameters
    ----------
    pdf_path
        Path to the PDF file whose SHA-256 hash will be embedded in the
        manifest.
    manifest_path
        Path to the C2PA manifest JSON template.
    output_path
        Destination for the generated .c2pa sidecar manifest file.
    c2patool
        Path to the c2patool executable.  When ``None``, the tool is
        located via ``shutil.which("c2patool")``.

    Returns
    -------
    True on success, False on failure.  Does not call sys.exit().
    """
    tool = c2patool or shutil.which("c2patool")
    if not tool:
        logger.error("c2patool not found in PATH")
        return False

    pdf_hash = calculate_sha256(pdf_path)
    logger.info("PDF SHA-256: %s", pdf_hash)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # Remove signing fields to force built-in test certificate
    manifest_data.pop("private_key", None)
    manifest_data.pop("sign_cert", None)
    manifest_data.pop("alg", None)

    pdf_hash_assertion = {
        "label": "org.ssccs.pdfhash",
        "data": {"hash": f"sha256:{pdf_hash}"},
    }

    if "assertions" not in manifest_data:
        manifest_data["assertions"] = []
    found = False
    for i, a in enumerate(manifest_data["assertions"]):
        if a.get("label") == "org.ssccs.pdfhash":
            manifest_data["assertions"][i] = pdf_hash_assertion
            found = True
            break
    if not found:
        manifest_data["assertions"].append(pdf_hash_assertion)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_dir = Path(tmpdir)

        # Create metadata SVG (contains both the PDF hash and the full
        # original JSON)
        metadata_file = tmp_dir / "metadata.svg"
        create_metadata_file(metadata_file, pdf_hash, manifest_path)

        # Save the modified manifest (with pdfhash) as a separate JSON
        # file for c2patool
        manifest_json = tmp_dir / "manifest.json"
        with open(manifest_json, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        output_base = tmp_dir / "output.svg"
        sidecar_c2pa = tmp_dir / "output.c2pa"

        cmd = [tool, str(metadata_file), "-m", str(manifest_json), "-s", "-o", str(output_base), "-f"]
        logger.info("Running: %s", " ".join(cmd))
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            logger.error("c2patool error: %s", result.stderr)
            return False

        if sidecar_c2pa.exists():
            shutil.copy2(sidecar_c2pa, output_path)
            logger.info("C2PA manifest created: %s", output_path)
        else:
            logger.error("%s not generated", sidecar_c2pa)
            return False

        # Copy the metadata SVG to the output folder with a descriptive name
        identifier_svg_path = output_path.parent / f"{output_path.stem}.c2pa_identifier.svg"
        shutil.copy2(metadata_file, identifier_svg_path)
        logger.info("Identifier SVG saved: %s", identifier_svg_path)

    # Verify
    verify_cmd = [tool, str(output_path)]
    verify_result = subprocess.run(verify_cmd, capture_output=True, text=True)
    if verify_result.returncode == 0:
        logger.info("Manifest verification succeeded")
    else:
        logger.warning("Manifest verification failed: %s", verify_result.stderr)

    return True
