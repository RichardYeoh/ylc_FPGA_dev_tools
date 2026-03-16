from __future__ import annotations

import argparse
from collections import Counter
import re
from pathlib import Path


SOURCE_EXTENSIONS = {".v", ".vh", ".sv", ".svh"}
AUTHOR_VALUE = "ylcheng"

LINE_COMMENT_RE = re.compile(r"^(?P<indent>\s*//\s*)(?P<body>.*?)(?P<newline>\r?\n?)$")
BLOCK_STYLE_RE = re.compile(
    r"^(?P<prefix>\s*\*\s*)(?P<label>author(?:'s email)?|email)\b(?P<pad>\s*:\s*)(?P<value>.*?)(?P<suffix>\s*)$",
    re.IGNORECASE,
)
LINE_STYLE_RE = re.compile(
    r"^(?P<lead>\s*)(?P<label>author/designer|author(?:'s email)?|email)\b(?P<gap>\s*)(?P<pad>:\s*)(?P<value>.*?)(?P<suffix>\s*)$",
    re.IGNORECASE,
)
COPYRIGHT_RE = re.compile(r"copyright|copyright@|copyright\s*\(c\)|copyright\(c\)", re.IGNORECASE)
COPYRIGHT_FOLLOW_RE = re.compile(
    r"(confidential|proprietary|all rights reserved)",
    re.IGNORECASE,
)
RELEASE_HEADER_RE = re.compile(r"^//(?P<indent>\s*)VERSION\s+Date\s+AUTHOR\s+DESCRIPTION\b", re.IGNORECASE)
RELEASE_ROW_RE = re.compile(r"^//(?P<indent>\s*)\S+\s+\d{4}-\d{2}-\d{2}\s+")
AUTHOR_MATCH_TARGETS = ("yanglicheng", "lichengyang")
AUTHOR_MATCH_THRESHOLD = 8


def iter_source_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in SOURCE_EXTENSIONS)


def is_comment_or_blank(line: str) -> bool:
    stripped = line.strip()
    return not stripped or stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("*/")


def split_header(lines: list[str]) -> tuple[list[str], list[str]]:
    header: list[str] = []
    body_start = 0
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            header.append(line)
            continue
        if is_comment_or_blank(line):
            header.append(line)
            continue
        body_start = idx
        break
    else:
        body_start = len(lines)
    return header, lines[body_start:]


def maybe_rewrite_comment_line(line: str) -> tuple[str | None, bool]:
    match = LINE_COMMENT_RE.match(line)
    if not match:
        return line, False

    body = match.group("body")
    newline = match.group("newline")

    line_style = LINE_STYLE_RE.match(body)
    if line_style:
        label = line_style.group("label").lower()
        if "email" in label:
            return None, True
        if not should_replace_author(line_style.group("value")):
            return line, False
        rebuilt = (
            f"{match.group('indent')}{line_style.group('lead')}{line_style.group('label')}"
            f"{line_style.group('gap')}: {AUTHOR_VALUE}{newline}"
        )
        return rebuilt, rebuilt != line

    block_style = BLOCK_STYLE_RE.match(body)
    if block_style:
        label = block_style.group("label").lower()
        if "email" in label:
            return None, True
        if not should_replace_author(block_style.group("value")):
            return line, False
        rebuilt = (
            f"{match.group('indent')}{block_style.group('prefix')}"
            f"{block_style.group('label')}: {AUTHOR_VALUE}{newline}"
        )
        return rebuilt, rebuilt != line

    if COPYRIGHT_RE.search(body):
        return None, True

    return line, False


def transform_header(lines: list[str]) -> tuple[list[str], bool]:
    updated: list[str] = []
    changed = False
    skip_followup = False
    release_columns: tuple[int, int] | None = None

    for line in lines:
        stripped = line.strip()
        if skip_followup:
            if stripped.startswith("//") and COPYRIGHT_FOLLOW_RE.search(stripped):
                changed = True
                continue
            skip_followup = False

        if release_columns is not None:
            if stripped.startswith("//") and RELEASE_ROW_RE.match(line):
                author_start, desc_start = release_columns
                line_body, newline = split_line_ending(line)
                if len(line_body) >= desc_start:
                    author_field = line_body[author_start:desc_start]
                    if should_replace_author(author_field):
                        new_field = f"{AUTHOR_VALUE:<{len(author_field)}}"
                        rebuilt = f"{line_body[:author_start]}{new_field}{line_body[desc_start:]}{newline}"
                    else:
                        rebuilt = line
                    updated.append(rebuilt)
                    changed = changed or rebuilt != line
                    continue
            else:
                release_columns = None

        rewritten, line_changed = maybe_rewrite_comment_line(line)
        if rewritten is None:
            changed = True
            if COPYRIGHT_RE.search(line):
                skip_followup = True
            continue

        updated.append(rewritten)
        changed = changed or line_changed
        header_match = RELEASE_HEADER_RE.match(rewritten)
        if header_match:
            line_body, _ = split_line_ending(rewritten)
            author_start = line_body.index("AUTHOR")
            desc_start = line_body.index("DESCRIPTION")
            release_columns = (author_start, desc_start)

    return updated, changed


def split_line_ending(line: str) -> tuple[str, str]:
    if line.endswith("\r\n"):
        return line[:-2], "\r\n"
    if line.endswith("\n"):
        return line[:-1], "\n"
    return line, ""


def should_replace_author(value: str) -> bool:
    canonical = re.sub(r"[^a-z]", "", value.lower())
    if not canonical:
        return False
    source_counter = Counter(canonical)
    for target in AUTHOR_MATCH_TARGETS:
        overlap = sum((source_counter & Counter(target)).values())
        if overlap > AUTHOR_MATCH_THRESHOLD:
            return True
    return False


def process_file(path: Path, apply_changes: bool) -> bool:
    original = path.read_text(encoding="utf-8", errors="ignore")
    lines = original.splitlines(keepends=True)
    header, body = split_header(lines)
    new_header, changed = transform_header(header)
    if not changed:
        return False

    if apply_changes:
        path.write_text("".join(new_header + body), encoding="utf-8", newline="")
    return True


def run_once(root: Path, apply_changes: bool) -> list[Path]:
    files = iter_source_files(root)
    changed_files = [path for path in files if process_file(path, apply_changes=apply_changes)]
    mode = "APPLY" if apply_changes else "CHECK"
    action = "updated" if apply_changes else "would update"
    print(f"[{mode}] root: {root.resolve()}")
    print(f"[{mode}] scanned source files: {len(files)}")
    print(f"[{mode}] {action} {len(changed_files)} file(s)")
    for path in changed_files:
        print(path.as_posix())
    return changed_files


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize RTL file headers.")
    parser.add_argument("root", nargs="?", default="rtl", help="Root directory to process.")
    parser.add_argument("--apply", action="store_true", help="Write changes in place.")
    args = parser.parse_args()

    root = Path(args.root)
    run_once(root, apply_changes=args.apply)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
