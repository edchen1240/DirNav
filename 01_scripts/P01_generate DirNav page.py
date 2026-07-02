#!/usr/bin/env python3
"""
[P01_generate DirNav page.py]
Purpose:
    Generate the static DirNav HTML page from projects.json.
    Reads ../projects.json, validates it, then writes ../02_html/index.html with
    the data embedded as window.DIRNAV_DATA. The page links style.css and
    03_js/app.js as separate files; app.js does the client-side render.
Author: Meng-Chi Ed Chen
Date:
Reference:
    1. Replaces the prior generate.ts + types.ts.
    2. Pure stdlib, no external dependencies.

Status: Working.
"""

import os, sys, re, json, shutil, time
from datetime import datetime
from pathlib import Path

#[1] Global dirs and paths
HERE            = Path(__file__).parent
ROOT            = HERE.parent
DIR_HTML        = ROOT / "02_html"
DIR_INCLUDES    = DIR_HTML / "04_includes"
PATH_JSON       = ROOT / "projects.json"

PATH_README     = ROOT / "12_GitHub_DirNav" / "README.md"
if not PATH_README.exists():
    PATH_README = ROOT / "README.md"
PATH_DEMO_GIF   = PATH_README.parent / "DirNav_demo.gif"
PATH_THEMES_PNG = PATH_README.parent / "themes_all.png"
PATH_MAIN_PAGE  = DIR_HTML / "index.html"
PATH_ABOUT_PAGE = DIR_HTML / "about.html"
PATH_WEEKLY_RETRIEVER = Path(r"D:\01_Floor\a_Ed\21_Claude\02_AI Career Advise\01_Weekly\P01_latest weekly retriever.py")


DATE_RE         = re.compile(r"^(\d{4}-\d{2}-\d{2})?$")
SLUG_RE         = re.compile(r"^\S+$")

PROJECT_FIELDS = (
    "projectSlug", "projectName", "attributes", "priority", "status",
    "p00InitiationDate", "startDate", "lastWorkDate", "note",
    "folders", "urls", "files", "related", "p00",
)
STATUS_FIELDS = ("value", "label", "description", "dim", "order")



#[2] Dashboard theme — single switch: set PATH_STYLE_CSS, then recompile.
# Available: style.css (default), style-forest.css, style-blue.css, style-macaron.css (attribute colors unchanged).
PATH_STYLE_CSS = DIR_HTML / "style.css"
#PATH_STYLE_CSS = DIR_HTML / "style-forest.css"
#PATH_STYLE_CSS = DIR_HTML / "style-blue.css"
#PATH_STYLE_CSS = DIR_HTML / "style-macaron.css"

def style_href():
    """Relative stylesheet URL from 02_html/ for generated pages."""
    if not PATH_STYLE_CSS.is_file():
        raise FileNotFoundError(f"Theme stylesheet not found: {PATH_STYLE_CSS}")
    return PATH_STYLE_CSS.relative_to(DIR_HTML).as_posix()


#[3] About page compiler

class CompileAboutPage:
    """
    Compile a markdown source file (PATH_README) into a static about.html.
    The result is a real page, not a fetched fragment, so it works under both
    file:// and http://. Supports the markdown subset the README actually uses:
    setext H1 (Title under '=' line), ATX headers (# .. ###), paragraphs,
    bullet and ordered lists, fenced code blocks (```), inline `code`, links
    [text](url), images ![alt](url), simple pipe-tables, blockquotes, and
    horizontal rules. HTML comments are stripped.
    """

    def __init__(self, src_path, out_path, style_href="style.css", title="About DirNav", assets=None):
        self.src_path = src_path
        self.out_path = out_path
        self.style_href = style_href
        self.title = title
        # Files (images, etc.) to copy alongside out_path so relative refs in
        # the source markdown resolve correctly under the rendered page.
        self.assets = list(assets) if assets else []

    def run(self):
        if not self.src_path.exists():
            print(f"WARNING: {self.src_path} not found; skipping about page.", file=sys.stderr)
            return False
        md = self.src_path.read_text(encoding="utf-8")
        body = self._md_to_html(md)
        page = self._wrap_page(body)
        self.out_path.write_text(page, encoding="utf-8")
        print(f"✅ Generated {self.out_path}")
        self._copy_assets()
        return True

    def _copy_assets(self):
        out_dir = self.out_path.parent
        for asset in self.assets:
            asset_path = Path(asset)
            if not asset_path.exists():
                print(f"  WARNING: asset {asset_path} not found; skipping copy.", file=sys.stderr)
                continue
            dest = out_dir / asset_path.name
            shutil.copy2(asset_path, dest)
            print(f"  Copied {asset_path.name} to {out_dir}")

    # ---------- HTML wrapper ----------
    def _wrap_page(self, body_html):
        return (
            '<!doctype html>\n'
            '<html lang="en">\n'
            '<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
            f'<title>{self._esc(self.title)}</title>\n'
            '<link rel="icon" type="image/png" href="02_image/DirNav-favicon.png">\n'
            f'<link rel="stylesheet" href="{self.style_href}">\n'
            '</head>\n'
            '<body>\n'
            '<header class="dn-header">\n'
            '  <div class="dn-header-row">\n'
            '    <div class="dn-brand"><a href="index.html" style="color:inherit;text-decoration:none;background:inherit;-webkit-text-fill-color:inherit;">DirNav</a></div>\n'
            '  </div>\n'
            '</header>\n'
            '<main class="dn-about-page">\n'
            f'{body_html}\n'
            '</main>\n'
            '</body>\n'
            '</html>\n'
        )

    # ---------- escaping ----------
    @staticmethod
    def _esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # ---------- inline ----------
    def _inline(self, s):
        s = self._esc(s)
        # Images first (so [![] ()] in alt doesn't break)
        s = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', s)
        # Inline code (greedy, single backticks)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        # Links
        s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', s)
        # Bold then italic (ordered to avoid ** being eaten by *)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", s)
        return s

    # ---------- block parser ----------
    def _md_to_html(self, md):
        # Strip HTML comments first (covers Ed's commented-out screenshot line, etc.)
        md = re.sub(r"<!--.*?-->", "", md, flags=re.DOTALL)
        lines = md.replace("\r\n", "\n").split("\n")

        out = []
        para = []
        in_ul = False
        in_ol = False
        in_code = False
        code_buf = []
        code_lang = ""
        i = 0
        n = len(lines)

        def flush_para():
            nonlocal para
            if para:
                out.append("<p>" + " ".join(para) + "</p>")
                para = []

        def close_lists():
            nonlocal in_ul, in_ol
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if in_ol:
                out.append("</ol>")
                in_ol = False

        while i < n:
            line = lines[i].rstrip()

            # Fenced code block fence
            m = re.match(r"^```(.*)$", line)
            if m:
                if not in_code:
                    flush_para(); close_lists()
                    in_code = True
                    code_lang = m.group(1).strip()
                    code_buf = []
                else:
                    code_html = self._esc("\n".join(code_buf))
                    cls = f' class="lang-{self._esc(code_lang)}"' if code_lang else ""
                    out.append(f"<pre><code{cls}>{code_html}</code></pre>")
                    in_code = False
                i += 1
                continue
            if in_code:
                code_buf.append(lines[i])
                i += 1
                continue

            # Setext H1 (line followed by ===)
            if i + 1 < n and re.match(r"^=+\s*$", lines[i + 1].rstrip()) and line and not line.startswith("#"):
                flush_para(); close_lists()
                out.append("<h1>" + self._inline(line) + "</h1>")
                i += 2
                continue

            # Setext H2 (line followed by --- but only if 3+ dashes; horizontal rule handled below)
            if (i + 1 < n
                    and re.match(r"^-{3,}\s*$", lines[i + 1].rstrip())
                    and line
                    and not line.startswith("-")
                    and not line.startswith("#")):
                flush_para(); close_lists()
                out.append("<h2>" + self._inline(line) + "</h2>")
                i += 2
                continue

            # Horizontal rule
            if re.match(r"^-{3,}\s*$", line) or re.match(r"^\*{3,}\s*$", line):
                flush_para(); close_lists()
                out.append("<hr>")
                i += 1
                continue

            # ATX headers # .. ######
            m = re.match(r"^(#{1,6})\s+(.*)$", line)
            if m:
                flush_para(); close_lists()
                level = len(m.group(1))
                text = m.group(2).rstrip("# ").strip()
                out.append(f"<h{level}>{self._inline(text)}</h{level}>")
                i += 1
                continue

            # Pipe table: header row + separator row
            if ("|" in line
                    and i + 1 < n
                    and re.match(r"^\s*\|?[\s\-:|]+\|?\s*$", lines[i + 1])
                    and "-" in lines[i + 1]):
                flush_para(); close_lists()
                header = self._parse_table_row(line)
                i += 2
                rows = []
                while i < n and "|" in lines[i] and lines[i].strip():
                    rows.append(self._parse_table_row(lines[i]))
                    i += 1
                out.append(self._table_to_html(header, rows))
                continue

            # Blockquote
            if line.startswith("> "):
                flush_para(); close_lists()
                buf = []
                while i < n and lines[i].rstrip().startswith("> "):
                    buf.append(lines[i].rstrip()[2:])
                    i += 1
                out.append("<blockquote><p>" + self._inline(" ".join(buf)) + "</p></blockquote>")
                continue

            # Bullet list item
            m = re.match(r"^\s*[-*]\s+(.*)$", line)
            if m:
                flush_para()
                if in_ol:
                    out.append("</ol>"); in_ol = False
                if not in_ul:
                    out.append("<ul>"); in_ul = True
                out.append("<li>" + self._inline(m.group(1)) + "</li>")
                i += 1
                continue

            # Ordered list item
            m = re.match(r"^\s*\d+\.\s+(.*)$", line)
            if m:
                flush_para()
                if in_ul:
                    out.append("</ul>"); in_ul = False
                if not in_ol:
                    out.append("<ol>"); in_ol = True
                out.append("<li>" + self._inline(m.group(1)) + "</li>")
                i += 1
                continue

            # Blank line
            if line == "":
                flush_para(); close_lists()
                i += 1
                continue

            # Plain paragraph line
            close_lists()
            para.append(self._inline(line))
            i += 1

        flush_para(); close_lists()
        return "\n".join(out)

    def _parse_table_row(self, line):
        s = line.strip()
        if s.startswith("|"):
            s = s[1:]
        if s.endswith("|"):
            s = s[:-1]
        return [c.strip() for c in s.split("|")]

    def _table_to_html(self, header, rows):
        parts = ['<table class="dn-table"><thead><tr>']
        for c in header:
            parts.append(f"<th>{self._inline(c)}</th>")
        parts.append("</tr></thead>")
        if rows:
            parts.append("<tbody>")
            for row in rows:
                parts.append("<tr>")
                for c in row:
                    parts.append(f"<td>{self._inline(c)}</td>")
                parts.append("</tr>")
            parts.append("</tbody>")
        parts.append("</table>")
        return "".join(parts)



def update_p00_sizes(data, verbose=True):
    """
    For every project, read its 'p00' path, measure the file size in kB, and
    write it back to a 'p00SizekB' field on the same project record.

        [Read p00 path]
            ↓
        [Measure size in kB (or None if missing/empty)]
            ↓
        [Write p00SizekB back onto the project]

    Returns True if any project record changed, so the caller can decide
    whether to rewrite projects.json.
    """
    changed = False
    for p in data.get("projects", []):
        if not isinstance(p, dict):
            continue
        slug = p.get("projectSlug", "?")
        p00 = p.get("p00", "")

        size_kb = None
        if p00:
            p00_path = Path(p00)
            if p00_path.is_file():
                size_kb = round(p00_path.stat().st_size / 1024, 2)
            elif verbose:
                print(f"  WARNING: p00 for {slug!r} not found: {p00}", file=sys.stderr)

        if p.get("p00SizekB") != size_kb:
            p["p00SizekB"] = size_kb
            changed = True

    return changed


def get_latest_weekly_path(verbose=True):
    """
    Import LatestWeeklyRetriever from the weekly tooling script and return
    the resolved path to the latest weekly markdown file, or None if unavailable.
    """
    if not PATH_WEEKLY_RETRIEVER.is_file():
        if verbose:
            print(f"WARNING: weekly retriever not found: {PATH_WEEKLY_RETRIEVER}", file=sys.stderr)
        return None
    import importlib.util
    spec = importlib.util.spec_from_file_location("dirnav_weekly_retriever", PATH_WEEKLY_RETRIEVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    LWR = mod.LatestWeeklyRetriever()
    return str(Path(LWR.path_latest_weekly).resolve())


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
    if not PATH_JSON.exists():
        print(f"ERROR: {PATH_JSON} not found", file=sys.stderr)
        sys.exit(1)

    try:
        with PATH_JSON.open("r", encoding="utf-8") as f:
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

    #[2b] Measure each project's p00 file size (kB) and persist it back to projects.json.
    if update_p00_sizes(data):
        with PATH_JSON.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            f.write("\n")
        print(f"Updated p00SizekB in {PATH_JSON}")

    #[3] Read HTML fragments and fill the generated-at placeholder in the footer.
    header = (DIR_INCLUDES / "header.html").read_text(encoding="utf-8")
    footer = (DIR_INCLUDES / "footer.html").read_text(encoding="utf-8")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    footer = footer.replace("{{GENERATED_AT}}", generated_at)

    #[4] Keep non-ASCII project paths readable in the embedded JSON blob.
    data_json = json.dumps(data, ensure_ascii=False)
    latest_weekly_path = get_latest_weekly_path()
    theme_href = style_href()

    #[5] Build the final standalone page; app.js performs the client-side render.
    page = (
        '<!doctype html>\n'
        '<html lang="en">\n'
        '<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<title>DirNav</title>\n'
        '<link rel="icon" type="image/png" href="02_image/DirNav-favicon.png">\n'
        f'<link rel="stylesheet" href="{theme_href}">\n'
        '</head>\n'
        '<body>\n'
        f'{header}\n'
        '<main id="app" class="dn-main"></main>\n'
        f'{footer}\n'
        f'<script>window.DIRNAV_DATA = {data_json};</script>\n'
        f'<script>window.DIRNAV_MANIFEST_PATH = {json.dumps(str(PATH_JSON.resolve()))};</script>\n'
        f'<script>window.DIRNAV_LATEST_WEEKLY_PATH = {json.dumps(latest_weekly_path)};</script>\n'
        '<script src="03_js/app.js"></script>\n'
        '</body>\n'
        '</html>\n'
    )

    #[6] Write output and print a compact build summary.
    PATH_MAIN_PAGE.write_text(page, encoding="utf-8")
    print(f"✅ Generated {PATH_MAIN_PAGE}")
    print(f"  {len(data['projects'])} projects, {len(data['attributePool'])} attributes, {len(data['statusPool'])} statuses.")

    print(f"  theme: {theme_href}")

    #[7] Compile the about page from README.md (or skip with a warning if absent).
    CompileAboutPage(
        src_path=PATH_README,
        out_path=PATH_ABOUT_PAGE,
        style_href=theme_href,
        title="About DirNav",
        assets=[PATH_DEMO_GIF, PATH_THEMES_PNG],
    ).run()


if __name__ == "__main__":
    print(f'\n[{os.path.basename(__file__)}] Start generating DirNav page.')
    main()
    print(f'\nCompleted {os.path.basename(__file__)}. Close in 3 seconds.')
    time.sleep(3)




