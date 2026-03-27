#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Create or update the Confluence page mirroring .vscode/README.md.

Confluence location:
    Developer Documentation > IDE > VSCode > "VSCode & Bazel: Local vs CI Parity"
    Page ID: 190555122

Usage:
    # Dry run — print generated XHTML to stdout:
    python .ide/vscode/scripts/update_confluence_vscode_page.py --dry-run

    # Create or update the page:
    CONFLUENCE_TOKEN=<token> \
    python .ide/vscode/scripts/update_confluence_vscode_page.py

Environment variables:
    CONFLUENCE_TOKEN  — Confluence personal access token (required for non-dry-run)
    CONFLUENCE_URL    — Base URL (default: https://wiki.lan.checkmk.net)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

CONFLUENCE_URL = os.environ.get("CONFLUENCE_URL", "https://wiki.lan.checkmk.net")
README_PATH = Path(__file__).resolve().parent.parent.parent / "README.md"
PAGE_TITLE = "VSCode & Bazel: Local vs CI Parity"
PAGE_ID = "190555122"

# Confluence status macro colour mapping for parity values
STATUS_COLORS: dict[str, str] = {
    "Match": "Green",
    "Version risk": "Yellow",
    "Partial": "Yellow",
    "Broken": "Red",
    "Not configured": "Grey",
    "Not evaluated": "Grey",
    "Known limitation": "Yellow",
}


# ---------------------------------------------------------------------------
# Markdown → Confluence storage format conversion
# ---------------------------------------------------------------------------


def _escape(text: str) -> str:
    """Escape HTML entities in plain text."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _inline(text: str) -> str:
    """Convert inline markdown (code, bold, links) to HTML."""

    def _code_repl(m: re.Match[str]) -> str:
        return f"<code>{_escape(m.group(1))}</code>"

    text = re.sub(r"`([^`]+)`", _code_repl, text)

    # Escape remaining bare < > outside tags we just created
    parts = re.split(r"(<code>.*?</code>|<strong>.*?</strong>|<a [^>]+>.*?</a>)", text)
    for idx, part in enumerate(parts):
        if not part.startswith("<"):
            parts[idx] = _escape(part)
    text = "".join(parts)

    # Bold **text**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Strikethrough ~~text~~
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    # Links [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def _status_macro(value: str) -> str:
    """Return a Confluence status macro for known parity values, or plain text."""
    colour = STATUS_COLORS.get(value.strip())
    if colour:
        return (
            f'<ac:structured-macro ac:name="status">'
            f'<ac:parameter ac:name="title">{value.strip()}</ac:parameter>'
            f'<ac:parameter ac:name="colour">{colour}</ac:parameter>'
            f"</ac:structured-macro>"
        )
    return _inline(value)


def _table_to_xhtml(header_line: str, _sep_line: str, body_lines: list[str]) -> str:
    """Convert a markdown table (header + separator + body) to Confluence XHTML."""
    parts: list[str] = ['<table class="wrapped"><colgroup><col/></colgroup><tbody>']

    def _parse_row(line: str) -> list[str]:
        cells = line.strip().strip("|").split("|")
        return [c.strip() for c in cells]

    headers = _parse_row(header_line)
    parts.append("<tr>" + "".join(f"<th>{_inline(h)}</th>" for h in headers) + "</tr>")

    parity_col = None
    for i, h in enumerate(headers):
        if h.strip().lower() == "parity":
            parity_col = i

    for line in body_lines:
        cells = _parse_row(line)
        row_parts: list[str] = []
        for i, cell in enumerate(cells):
            if i == parity_col:
                row_parts.append(f"<td>{_status_macro(cell)}</td>")
            else:
                row_parts.append(f"<td>{_inline(cell)}</td>")
        parts.append("<tr>" + "".join(row_parts) + "</tr>")

    parts.append("</tbody></table>")
    return "\n".join(parts)


def _md_to_confluence(md: str) -> str:
    """Convert the full README markdown to Confluence storage format XHTML."""
    lines = md.splitlines()
    out: list[str] = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Headings
        heading_match = re.match(r"^(#{1,6})\s+(.*)", line)
        if heading_match:
            level = len(heading_match.group(1))
            text = _inline(heading_match.group(2))
            out.append(f"<h{level}>{text}</h{level}>")
            i += 1
            continue

        # Table: header | separator | body rows
        if (
            "|" in line
            and i + 1 < len(lines)
            and re.match(r"^\|[\s\-:|]+\|$", lines[i + 1].strip())
        ):
            header_line = line
            sep_line = lines[i + 1]
            body: list[str] = []
            j = i + 2
            while j < len(lines) and lines[j].strip().startswith("|"):
                body.append(lines[j])
                j += 1
            out.append(_table_to_xhtml(header_line, sep_line, body))
            i = j
            continue

        # Ordered list items
        ol_match = re.match(r"^(\d+)\.\s+(.*)", line)
        if ol_match:
            out.append("<ol>")
            while i < len(lines):
                ol_m = re.match(r"^(\d+)\.\s+(.*)", lines[i])
                if not ol_m:
                    break
                out.append(f"<li>{_inline(ol_m.group(2))}</li>")
                i += 1
            out.append("</ol>")
            continue

        # Unordered list items
        if re.match(r"^[-*]\s+", line):
            out.append("<ul>")
            while i < len(lines) and re.match(r"^[-*]\s+", lines[i]):
                text = re.sub(r"^[-*]\s+", "", lines[i])
                out.append(f"<li>{_inline(text)}</li>")
                i += 1
            out.append("</ul>")
            continue

        # Blank lines → skip
        if not line.strip():
            i += 1
            continue

        # Regular paragraph
        out.append(f"<p>{_inline(line)}</p>")
        i += 1

    return "\n".join(out)


# ---------------------------------------------------------------------------
# Confluence REST API helpers
# ---------------------------------------------------------------------------


def _api_request(method: str, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    token = os.environ.get("CONFLUENCE_TOKEN", "")
    if not token:
        print("ERROR: CONFLUENCE_TOKEN env var is required.", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    url = f"{CONFLUENCE_URL.rstrip('/')}{path}"
    if not url.startswith("https://"):
        print(f"ERROR: refusing non-HTTPS URL: {url}", file=sys.stderr)  # noqa: T201
        sys.exit(1)

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    body = json.dumps(data).encode() if data else None

    req = Request(url, data=body, headers=headers, method=method)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urlopen(req) as resp:  # nosec B310 # scheme validated above
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        error_body = exc.read().decode()
        print(f"ERROR: {exc.code} {exc.reason}\n{error_body}", file=sys.stderr)  # noqa: T201
        sys.exit(1)


def _get_page_version(page_id: str) -> int:
    """Get the current version number of a page."""
    result = _api_request("GET", f"/rest/api/content/{page_id}?expand=version")
    version = result["version"]
    assert isinstance(version, dict)
    number = version["number"]
    assert isinstance(number, int)
    return number


def _update_page(page_id: str, title: str, body_xhtml: str, version: int) -> dict[str, Any]:
    """Update an existing Confluence page."""
    payload = {
        "type": "page",
        "title": title,
        "version": {"number": version + 1},
        "body": {
            "storage": {
                "value": body_xhtml,
                "representation": "storage",
            }
        },
    }
    return _api_request("PUT", f"/rest/api/content/{page_id}", payload)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Update Confluence page from .vscode/README.md")
    parser.add_argument(
        "--dry-run", action="store_true", help="Print XHTML without calling the API"
    )
    args = parser.parse_args()

    md_content = README_PATH.read_text()
    xhtml = _md_to_confluence(md_content)

    if args.dry_run:
        print(xhtml)  # noqa: T201
        return

    version = _get_page_version(PAGE_ID)
    result = _update_page(PAGE_ID, PAGE_TITLE, xhtml, version)
    page_id = result["id"]
    print(f"Page updated (v{version + 1}): {CONFLUENCE_URL}/pages/viewpage.action?pageId={page_id}")  # noqa: T201


if __name__ == "__main__":
    main()
