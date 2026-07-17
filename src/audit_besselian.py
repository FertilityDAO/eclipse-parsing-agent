#!/usr/bin/env python3
"""
audit_besselian.py — LOOP B, Stage B1 (column audit).

Inventories every file under data/ and records, for each, its format, the
columns/fields present, and whether the canonical Besselian element fields
needed by the B3 solver are available. Writes outputs/besselian_audit.json.

This script only READS data/. It never modifies data/, verify/, or fixtures/.
"""

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "besselian_audit.json"

# The canonical Besselian elements the B3 solver needs. NASA's 5-Millennium
# canon ships each time-dependent element as polynomial coefficients, so a
# concept like "x" appears as x0..x3. We map each canonical concept to the
# set of column names that would satisfy it.
CANONICAL_REQUIREMENTS = {
    "t0 (reference time)": ["t0"],
    "x (shadow axis, poly)": ["x0", "x1", "x2", "x3"],
    "y (shadow axis, poly)": ["y0", "y1", "y2", "y3"],
    "d (declination, poly)": ["d0", "d1", "d2"],
    "mu (hour angle, poly)": ["mu0", "mu1", "mu2"],
    "l1 (penumbra radius, poly)": ["l10", "l11", "l12", "l1"],
    "l2 (umbra radius, poly)": ["l20", "l21", "l22", "l2"],
    "tan_f1 (penumbra cone angle)": ["tan_f1", "tanf1"],
    "tan_f2 (umbra cone angle)": ["tan_f2", "tanf2"],
}


def sniff_format(path: Path):
    """Return (format_label, header_columns). Only CSV/TSV are parsed for columns."""
    suffix = path.suffix.lower()
    if suffix not in (".csv", ".tsv", ".txt"):
        return suffix.lstrip(".") or "unknown", []
    with path.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            delim = dialect.delimiter
        except csv.Error:
            delim = ","
        reader = csv.reader(f, delimiter=delim)
        try:
            header = next(reader)
        except StopIteration:
            header = []
    fmt = {",": "csv", "\t": "tsv"}.get(delim, f"delimited({delim!r})")
    header = [c.strip().strip('"') for c in header]
    return fmt, header


def audit_file(path: Path):
    fmt, columns = sniff_format(path)
    present = {c.lower() for c in columns}

    requirement_status = {}
    all_satisfied = bool(columns)
    for concept, candidates in CANONICAL_REQUIREMENTS.items():
        matched = [c for c in candidates if c.lower() in present]
        satisfied = bool(matched)
        requirement_status[concept] = {
            "satisfied": satisfied,
            "matched_columns": matched,
        }
        all_satisfied = all_satisfied and satisfied

    return {
        "file": str(path.relative_to(ROOT)).replace("\\", "/"),
        "size_bytes": path.stat().st_size,
        "format": fmt,
        "column_count": len(columns),
        "columns_present": columns,
        "besselian_requirements": requirement_status,
        "elements_available": all_satisfied,
    }


def main():
    files = sorted(p for p in DATA.iterdir() if p.is_file())
    file_audits = [audit_file(p) for p in files]

    sources_with_elements = [a["file"] for a in file_audits if a["elements_available"]]
    elements_available = bool(sources_with_elements)

    if elements_available:
        rationale = (
            "At least one data file exposes the full set of canonical Besselian "
            "elements as NASA polynomial coefficients: "
            f"{', '.join(sources_with_elements)}. Each required concept "
            "(t0, x0..x3, y0..y3, d0..d2, mu0..mu2, l1/l2 radius coefficients, "
            "tan_f1, tan_f2) is present, so the B3 solver can be built as "
            "specified without sourcing elements externally."
        )
    else:
        rationale = (
            "No data file exposes the full set of canonical Besselian elements. "
            "The available files carry only derived summary fields (e.g. central "
            "duration, path width, greatest-eclipse lat/lon), not the polynomial "
            "coefficients (x0..x3, y0..y3, d0..d2, mu0..mu2, l1, l2, tan_f1, "
            "tan_f2, t0) the solver requires. Elements must be sourced separately "
            "from Espenak's canon per eclipse. STOP and escalate."
        )

    audit = {
        "stage": "B1",
        "purpose": "Column audit — which canonical Besselian element fields are present in data/?",
        "canonical_requirements": {k: v for k, v in CANONICAL_REQUIREMENTS.items()},
        "files_inspected": [a["file"] for a in file_audits],
        "file_count": len(file_audits),
        "files": file_audits,
        "columns_present": sorted(
            {c for a in file_audits for c in a["columns_present"]}
        ),
        "sources_with_elements": sources_with_elements,
        "elements_available": elements_available,
        "rationale": rationale,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT)}")
    print(f"  files inspected: {len(file_audits)}")
    print(f"  elements_available: {elements_available}")
    for a in file_audits:
        print(f"    - {a['file']}: {a['column_count']} cols, "
              f"elements_available={a['elements_available']}")


if __name__ == "__main__":
    main()
