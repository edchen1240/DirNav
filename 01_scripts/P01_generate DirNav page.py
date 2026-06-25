#!/usr/bin/env python3
"""
[P01_generate DirNav page.py]
Purpose:
    Generate the static DirNav HTML page from projects.json.
    Reads ../projects.json, validates it, then writes ../07_html/index.html with
    the data embedded as window.DIRNAV_DATA. The page links style.css and
    03_js/app.js as separate files; app.js does the client-side render.
Author: Meng-Chi Ed Chen
Date:
Reference:
    1. Replaces the prior generate.ts + types.ts.
    2. Pure stdlib, no external dependencies.

Status: Working.
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent
HTML_DIR = ROOT / "07_html"
INCLUDES_DIR = HTML_DIR / "04_includes"
JSON_PATH = ROOT / "projects.json"
OUT_PATH = HTML_DIR / "index.html"

DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})?$")
SLUG_RE = re.compile(r"^\S+$")

PROJECT_FIELDS = (
    "projectSlug", "projectName", "attributes", "priority", "status",
    "p00InitiationDate", "startDate", "lastWorkDate", "note",
    "folders", "urls", "files", "related", "p00",
)
STATUS_FIELDS = ("value", "label", "description", "dim", "order")


class ValidationError(Exception):
    pass


def _typecheck(value, types, path, problems):
    if not isinstance(value, types):
        names = types.__name__ if not isinstance(types, tuple) else "/".join(t.__name__ for t in types)
        problems.append(f"{path}: expected {names}, got {type(value).__name__}")
        return False
    return True


def _require_keys(obj, required, path, problems):
    for k in required:
        if k not in obj:
            problems.append(f"{path}.{k}: missing required field")


def validate(data):
    """
    Mirror of the prior zod schema plus cross-validation.

    [Validation flow]
        |
    [Check top-level schema]
        |
    [Validate attribute/status pools]
        |
    [Validate each project record]
        |
    [Cross-check related project slugs]
        |
    [Raise one ValidationError containing every problem]

    Collects every problem and raises ValidationError once, so a single run
    reveals all issues instead of one-at-a-time.
    """
    #[0] Collect all validation errors first; raise once at the end for a complete report.
    problems = []

    #[1] Validate the top-level object and required sections.
    if not isinstance(data, dict):
        raise ValidationError("projects.json: top-level must be a JSON object")

    _require_keys(data, ("schemaVersion", "attributePool", "statusPool", "projects"), "", problems)
    if problems:
        raise ValidationError("\n".join("  " + p for p in problems))

    _typecheck(data["schemaVersion"], int, "schemaVersion", problems)

    #[2] Validate the attribute pool and keep a lookup set for project-level checks.
    pool = data["attributePool"]
    if _typecheck(pool, list, "attributePool", problems):
        for i, a in enumerate(pool):
            _typecheck(a, str, f"attributePool[{i}]", problems)
    pool_set = set(pool) if isinstance(pool, list) else set()

    #[3] Validate status definitions and keep the accepted status values.
    statuses = data["statusPool"]
    status_values = set()
    if _typecheck(statuses, list, "statusPool", problems):
        for i, s in enumerate(statuses):
            base = f"statusPool[{i}]"
            if not _typecheck(s, dict, base, problems):
                continue
            _require_keys(s, STATUS_FIELDS, base, problems)
            if isinstance(s.get("value"), str):
                status_values.add(s["value"])
            _typecheck(s.get("value", ""), str, f"{base}.value", problems)
            _typecheck(s.get("label", ""), str, f"{base}.label", problems)
            _typecheck(s.get("description", ""), str, f"{base}.description", problems)
            _typecheck(s.get("dim", False), bool, f"{base}.dim", problems)
            _typecheck(s.get("order", 0), int, f"{base}.order", problems)

    projects = data["projects"]
    if not _typecheck(projects, list, "projects", problems):
        raise ValidationError("\n".join("  " + p for p in problems))

    #[4] Validate project records and collect slugs for duplicate/cross-reference checks.
    slugs_seen = {}
    for i, p in enumerate(projects):
        base = f"projects[{i}]"
        if not _typecheck(p, dict, base, problems):
            continue
        _require_keys(p, PROJECT_FIELDS, base, problems)

        slug = p.get("projectSlug", "")
        if isinstance(slug, str):
            if not SLUG_RE.match(slug):
                problems.append(f"{base}.projectSlug: must be non-empty and URL-safe (no spaces); got {slug!r}")
            if slug in slugs_seen:
                problems.append(f"{base}.projectSlug: duplicate slug {slug!r} (also at projects[{slugs_seen[slug]}])")
            else:
                slugs_seen[slug] = i

        ref = f"{base} ({slug or '?'})"

        _typecheck(p.get("projectName", ""), str, f"{ref}.projectName", problems)

        attrs = p.get("attributes", [])
        if _typecheck(attrs, list, f"{ref}.attributes", problems):
            for j, a in enumerate(attrs):
                if _typecheck(a, str, f"{ref}.attributes[{j}]", problems) and pool_set and a not in pool_set:
                    problems.append(f"{ref}.attributes[{j}]: {a!r} not in attributePool")

        #[4b] bool is a subclass of int in Python; reject it explicitly for priority.
        pri = p.get("priority")
        if pri is not None and not (isinstance(pri, int) and not isinstance(pri, bool) and 0 <= pri <= 10):
            problems.append(f"{ref}.priority: expected int 0-10 or null, got {pri!r}")

        st = p.get("status", "")
        if _typecheck(st, str, f"{ref}.status", problems) and status_values and st not in status_values:
            problems.append(f"{ref}.status: {st!r} not in statusPool")

        for k in ("p00InitiationDate", "startDate", "lastWorkDate"):
            v = p.get(k, "")
            if _typecheck(v, str, f"{ref}.{k}", problems) and not DATE_RE.match(v):
                problems.append(f"{ref}.{k}: expected YYYY-MM-DD or empty, got {v!r}")

        _typecheck(p.get("note", ""), str, f"{ref}.note", problems)
        _typecheck(p.get("p00", ""), str, f"{ref}.p00", problems)

        for arr_key in ("folders", "urls", "files", "related"):
            arr = p.get(arr_key, [])
            if _typecheck(arr, list, f"{ref}.{arr_key}", problems):
                for j, x in enumerate(arr):
                    _typecheck(x, str, f"{ref}.{arr_key}[{j}]", problems)

    #[5] Related project slugs must resolve to a real project.
    all_slugs = set(slugs_seen)
    for i, p in enumerate(projects):
        if not isinstance(p, dict):
            continue
        slug = p.get("projectSlug", "")
        related = p.get("related", []) or []
        if not isinstance(related, list):
            continue
        for j, r in enumerate(related):
            if isinstance(r, str) and r not in all_slugs:
                problems.append(f"projects[{i}] ({slug}).related[{j}]: {r!r} does not resolve to a project")

    if problems:
        raise ValidationError("\n".join("  " + p for p in problems))


def main():
    """
    Main build procedure:

        [Read projects.json]
            ↓
        [Validate schema + cross references]
            ↓
        [Read header/footer includes]
            ↓
        [Embed DIRNAV_DATA into index.html]
            ↓
        [Write the generated page]
    """
    #[1] Load the source JSON file.
    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found", file=sys.stderr)
        sys.exit(1)

    try:
        with JSON_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print("projects.json is not valid JSON:", file=sys.stderr)
        print(f"  {e}", file=sys.stderr)
        sys.exit(1)

    #[2] Validate input before generating any HTML output.
    try:
        validate(data)
    except ValidationError as e:
        print("projects.json failed validation:", file=sys.stderr)
        print(str(e), file=sys.stderr)
        sys.exit(1)

    #[3] Read HTML fragments and fill the generated-at placeholder in the footer.
    header = (INCLUDES_DIR / "header.html").read_text(encoding="utf-8")
    footer = (INCLUDES_DIR / "footer.html").read_text(encoding="utf-8")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = footer.replace("{{GENERATED_AT}}", generated_at)

    #[4] Keep non-ASCII project paths readable in the embedded JSON blob.
    data_json = json.dumps(data, ensure_ascii=False)

    #[5] Build the final standalone page; app.js performs the client-side render.
    page = (
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>DirNav</title>\n'
        '<link rel="icon" type="image/png" href="02_image/DirNav-favicon.png">\n'
        '<link rel="stylesheet" href="style.css">\n'
        '</head>\n'
        '<body>\n'
        f'{header}\n'
        '<main id="app" class="dn-main"></main>\n'
        f'{footer}\n'
        f'<script>window.DIRNAV_DATA = {data_json};</script>\n'
        '<script src="03_js/app.js"></script>\n'
        '</body>\n'
        '</html>\n'
    )

    #[6] Write output and print a compact build summary.
    OUT_PATH.write_text(page, encoding="utf-8")
    print(f"Generated {OUT_PATH}")
    print(f"  {len(data['projects'])} projects, {len(data['attributePool'])} attributes, {len(data['statusPool'])} statuses.")


if __name__ == "__main__":
    main()
