#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Fetch Jira ticket context for Claude Code skill.

NOTE: This skill is limited to the CMK project to avoid interfering with sensitive
customer data. Only CMK- prefixed tickets are supported.

Usage: .venv/bin/python3 .claude/skills/jira-plan-ticket/fetch_jira_context.py <TICKET_KEY>

Environment: JIRA_PAT - Personal Access Token for Jira authentication.

Outputs structured markdown to stdout with ticket details, comments, and linked tickets.
"""

import os
import re
import sys
import tempfile
from concurrent.futures import as_completed, ThreadPoolExecutor
from pathlib import Path

from jira import JIRA, JIRAError
from jira.resources import Attachment, Comment, Issue, IssueLink, Version

JIRA_URL = "https://jira.lan.tribe29.com"
PROJECT_PREFIX = "CMK-"
MAX_LINKED_TICKETS = 15
MAX_MAIN_COMMENTS = 20
MAX_LINKED_COMMENTS = 10
MAX_MAIN_DESCRIPTION_CHARS = 3000
MAX_LINKED_DESCRIPTION_CHARS = 2000
MAX_COMMENT_CHARS = 1500

# Link types considered high priority (sorted before "relates to" etc.)
PRIORITY_LINK_TYPES = {
    "implements",
    "blocks",
    "is blocked by",
    "parent",
    "child",
    "is parent of",
    "is child of",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
# Matches Jira wiki image syntax: !filename.png! or !filename.png|options!
IMAGE_REFERENCE_RE = re.compile(r"!([^|!\n]+?)(?:\|[^!\n]*)?!")

# Name anonymization: maps real display names to "User 1", "User 2", etc.
_name_map: dict[str, str] = {}
_name_counter = 0


def anonymize_name(display_name: str) -> str:
    """Replace a person's display name with a consistent pseudonym."""
    global _name_counter
    if not display_name or display_name == "None":
        return display_name
    if display_name not in _name_map:
        _name_counter += 1
        _name_map[display_name] = f"User {_name_counter}"
    return _name_map[display_name]


# Matches Jira user mentions: [~username] or [~accountId:xxx]
_USER_MENTION_RE = re.compile(r"\[~([^\]]+)\]")


def anonymize_user_mentions(text: str) -> str:
    """Replace [~username] Jira mentions with anonymized names."""
    if not text:
        return text

    def _replace_mention(match: re.Match[str]) -> str:
        username = match.group(1)
        return anonymize_name(username)

    return _USER_MENTION_RE.sub(_replace_mention, text)


_CODE_BLOCK_RE = re.compile(r"\{code(?::([^}]*))?\}(.*?)\{code\}", re.DOTALL)
_NOFORMAT_RE = re.compile(r"\{noformat\}(.*?)\{noformat\}", re.DOTALL)
_QUOTE_RE = re.compile(r"\{quote\}(.*?)\{quote\}", re.DOTALL)
_HEADING_RE = re.compile(r"^h([1-6])\.\s+(.+)$", re.MULTILINE)
_BOLD_RE = re.compile(r"(?<!\w)\*([^\*\n]+?)\*(?!\w)")
_ITALIC_RE = re.compile(r"(?<!\w)_([^_\n]+?)_(?!\w)")
_STRIKE_RE = re.compile(r"(?<!\w)-([^\-\n]+?)-(?!\w)")
_LINK_RE = re.compile(r"\[([^|\]\n]+)\|([^\]\n]+)\]")
_TABLE_HEADER_RE = re.compile(r"^\|\|(.+)\|\|\s*$", re.MULTILINE)
_NESTED_NUMBERED_RE = re.compile(r"^##\s+", re.MULTILINE)
_NUMBERED_RE = re.compile(r"^#\s+", re.MULTILINE)
_NESTED_BULLET_RE = re.compile(r"^\*\*\s+", re.MULTILINE)


def jira_wiki_to_markdown(text: str) -> str:
    """Convert Jira wiki markup to GitHub-flavored markdown."""
    if not text:
        return text

    # Code blocks (must be first to protect contents from other substitutions)
    placeholders: list[str] = []

    def _save_code(match: re.Match[str]) -> str:
        lang = match.group(1) or ""
        code = match.group(2)
        placeholder = f"\x00CODE{len(placeholders)}\x00"
        placeholders.append(f"```{lang}\n{code}\n```")
        return placeholder

    def _save_noformat(match: re.Match[str]) -> str:
        code = match.group(1)
        placeholder = f"\x00CODE{len(placeholders)}\x00"
        placeholders.append(f"```\n{code}\n```")
        return placeholder

    text = _CODE_BLOCK_RE.sub(_save_code, text)
    text = _NOFORMAT_RE.sub(_save_noformat, text)

    # Quotes
    def _convert_quote(match: re.Match[str]) -> str:
        content = match.group(1).strip()
        return "\n".join(f"> {line}" for line in content.splitlines())

    text = _QUOTE_RE.sub(_convert_quote, text)

    # Headings
    text = _HEADING_RE.sub(lambda m: "#" * int(m.group(1)) + " " + m.group(2), text)

    # Inline formatting
    text = _BOLD_RE.sub(r"**\1**", text)
    text = _ITALIC_RE.sub(r"*\1*", text)
    text = _STRIKE_RE.sub(r"~~\1~~", text)

    # Links
    text = _LINK_RE.sub(r"[\1](\2)", text)

    # Table headers: ||h1||h2|| -> | h1 | h2 | + separator
    def _convert_table_header(match: re.Match[str]) -> str:
        cells = [c.strip() for c in match.group(1).split("||")]
        header = "| " + " | ".join(cells) + " |"
        separator = "| " + " | ".join("---" for _ in cells) + " |"
        return header + "\n" + separator

    text = _TABLE_HEADER_RE.sub(_convert_table_header, text)

    # Lists (order matters: nested before top-level)
    text = _NESTED_NUMBERED_RE.sub("   1. ", text)
    text = _NUMBERED_RE.sub("1. ", text)
    text = _NESTED_BULLET_RE.sub("  - ", text)
    # Top-level bullets: Jira "* item" → "- item" (but not "**" which is nested)
    # Only match "* " at start of line that isn't already handled
    text = re.sub(r"^\*\s+", "- ", text, flags=re.MULTILINE)

    # Restore code blocks
    for i, block in enumerate(placeholders):
        text = text.replace(f"\x00CODE{i}\x00", block)

    return text


def connect(token: str) -> JIRA:
    return JIRA(server=JIRA_URL, token_auth=token)


def download_attachments(
    issue: Issue, attachment_dir: Path
) -> tuple[dict[str, Path], dict[str, Path]]:
    """Download all attachments from an issue.

    Returns (images, other_files) where each is {filename: local_path}.
    """
    images: dict[str, Path] = {}
    other_files: dict[str, Path] = {}
    attachments: list[Attachment] = getattr(issue.fields, "attachment", [])
    for attachment in attachments:
        filename: str = attachment.filename
        try:
            content: bytes = attachment.get()  # type: ignore[no-untyped-call]
            local_path = attachment_dir / f"{issue.key}_{attachment.id}_{filename}"
            local_path.write_bytes(content)
            if Path(filename).suffix.lower() in IMAGE_EXTENSIONS:
                images[filename] = local_path
            else:
                other_files[filename] = local_path
        except Exception as e:
            print(f"Warning: Failed to download attachment {filename}: {e}", file=sys.stderr)
    return images, other_files


def replace_image_refs(text: str, image_map: dict[str, Path]) -> str:
    """Replace Jira !image! references with file paths for Claude Code to read."""

    def replacer(match: re.Match[str]) -> str:
        filename = match.group(1).strip()
        if filename in image_map:
            return f"\n\n[Image: {filename}]\nFile path: {image_map[filename]}\n"
        return match.group(0)  # keep original if not downloaded

    return IMAGE_REFERENCE_RE.sub(replacer, text)


def truncate(text: str | None, limit: int) -> str:
    if not text:
        return "(empty)"
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n... (truncated, {len(text) - limit} chars omitted)"


def format_field(value: object) -> str:
    if value is None:
        return "None"
    if hasattr(value, "displayName"):
        return str(value.displayName)
    if hasattr(value, "name"):
        return str(value.name)
    if isinstance(value, list):
        return ", ".join(format_field(v) for v in value) or "None"
    return str(value)


def format_issue_header(issue: Issue) -> str:
    f = issue.fields
    browse_url = f"{JIRA_URL}/browse/{issue.key}"
    affects_versions: list[Version] = getattr(f, "versions", [])
    lines = [
        f"**{issue.key}**: {f.summary}",
        f"URL: {browse_url}",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Status | {format_field(f.status)} |",
        f"| Type | {format_field(f.issuetype)} |",
        f"| Priority | {format_field(f.priority)} |",
        f"| Assignee | {anonymize_name(format_field(f.assignee))} |",
        f"| Labels | {format_field(f.labels)} |",
        f"| Affects Versions | {format_field(affects_versions)} |",
        f"| Fix Versions | {format_field(f.fixVersions)} |",
        f"| Components | {format_field(f.components)} |",
    ]
    return "\n".join(lines)


def format_comments(
    issue: Issue, max_comments: int, image_map: dict[str, Path] | None = None
) -> str:
    comments: list[Comment] = issue.fields.comment.comments
    if not comments:
        return "(no comments)"

    parts: list[str] = []
    shown = comments[-max_comments:]  # most recent
    if len(comments) > max_comments:
        parts.append(f"*Showing {max_comments} of {len(comments)} comments (most recent)*\n")

    for c in shown:
        author = anonymize_name(format_field(c.author))
        body: str = c.body or ""
        if image_map:
            body = replace_image_refs(body, image_map)
        body = anonymize_user_mentions(body)
        body = jira_wiki_to_markdown(body)
        parts.append(f"**{author}** ({c.created[:10]}):\n{truncate(body, MAX_COMMENT_CHARS)}\n")
    return "\n".join(parts)


def collect_linked_keys(issue: Issue) -> list[tuple[str, str, str]]:
    """Return (link_type_description, direction, key) tuples for CMK-project links."""
    results: list[tuple[str, str, str]] = []
    issue_links: list[IssueLink] = getattr(issue.fields, "issuelinks", [])
    for link in issue_links:
        if hasattr(link, "outwardIssue"):
            key: str = link.outwardIssue.key
            desc: str = link.type.outward
        elif hasattr(link, "inwardIssue"):
            key = link.inwardIssue.key
            desc = link.type.inward
        else:
            continue

        if not key.startswith(PROJECT_PREFIX):
            continue
        results.append((desc, "outward" if hasattr(link, "outwardIssue") else "inward", key))

    # Also check parent link
    parent: Issue | None = getattr(issue.fields, "parent", None)
    if parent and parent.key.startswith(PROJECT_PREFIX):
        results.append(("parent", "inward", parent.key))

    # Sort: priority link types first
    def sort_key(item: tuple[str, str, str]) -> tuple[int, str]:
        is_priority = 0 if item[0].lower() in PRIORITY_LINK_TYPES else 1
        return (is_priority, item[0])

    results.sort(key=sort_key)
    return results[:MAX_LINKED_TICKETS]


def get_affects_versions(issue: Issue) -> list[str]:
    """Extract affects version names from the issue."""
    versions: list[Version] = getattr(issue.fields, "versions", [])
    return [v.name for v in versions]


def format_linked_issue(client: JIRA, key: str, link_desc: str) -> str:
    try:
        issue = client.issue(key)
    except JIRAError as e:
        return f"### [{link_desc}] {key}\n\n*Failed to fetch: {e.status_code}*\n"

    linked_desc = anonymize_user_mentions(issue.fields.description or "")
    linked_desc = jira_wiki_to_markdown(linked_desc)
    parts = [
        f"### [{link_desc}] {format_issue_header(issue)}",
        "",
        "#### Description",
        truncate(linked_desc, MAX_LINKED_DESCRIPTION_CHARS),
        "",
        "#### Comments",
        format_comments(issue, MAX_LINKED_COMMENTS),
    ]
    return "\n".join(parts)


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: fetch_jira_context.py <TICKET_KEY>", file=sys.stderr)
        sys.exit(1)

    key = sys.argv[1].upper()
    if not key.startswith(PROJECT_PREFIX):
        print(
            f"Error: Only CMK- tickets are supported (limited to the CMK project"
            f" to avoid interfering with sensitive customer data), got: {key}",
            file=sys.stderr,
        )
        sys.exit(1)

    token = os.environ.get("JIRA_PAT")
    if not token:
        print("Error: JIRA_PAT environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    try:
        client = connect(token)
    except Exception as e:
        print(f"Error: Failed to connect to Jira: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        issue = client.issue(key)
    except JIRAError as e:
        if e.status_code == 404:
            print(f"Error: Ticket {key} not found.", file=sys.stderr)
        else:
            print(f"Error: Failed to fetch {key}: {e.status_code} {e.text}", file=sys.stderr)
        sys.exit(1)

    # Create temp directory for attachments (persists for Claude Code to read)
    attachment_dir = Path(tempfile.mkdtemp(prefix=f"jira_{key}_"))
    image_map, other_files_map = download_attachments(issue, attachment_dir)

    # Apply image replacements, name anonymization, and wiki-to-markdown conversion
    description: str = issue.fields.description or ""
    description = replace_image_refs(description, image_map)
    description = anonymize_user_mentions(description)
    description = jira_wiki_to_markdown(description)

    # Build output
    parts: list[str] = [
        f"# Jira Ticket: {key}",
        "",
        format_issue_header(issue),
        "",
        "## Description",
        "",
        truncate(description, MAX_MAIN_DESCRIPTION_CHARS),
        "",
        "## Comments",
        "",
        format_comments(issue, MAX_MAIN_COMMENTS, image_map),
    ]

    # Affects versions (used by the skill to determine the base branch)
    affects_versions = get_affects_versions(issue)
    if affects_versions:
        parts.append("")
        parts.append("## Affects Versions")
        parts.append("")
        for v in affects_versions:
            parts.append(f"- {v}")

    if image_map:
        parts.append("")
        parts.append("## Attachments (Images)")
        parts.append("")
        parts.append("*Use the Read tool to view these images:*")
        for filename, path in image_map.items():
            parts.append(f"- `{filename}`: `{path}`")

    if other_files_map:
        parts.append("")
        parts.append("## Attachments (Other Files)")
        parts.append("")
        parts.append("*These files have been downloaded and can be inspected:*")
        for filename, path in other_files_map.items():
            parts.append(f"- `{filename}`: `{path}`")

    # Linked tickets (fetched in parallel)
    linked = collect_linked_keys(issue)
    if linked:
        parts.append("")
        parts.append(f"## Linked Tickets ({len(linked)})")
        parts.append("")
        results: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=min(len(linked), 5)) as pool:
            futures = {
                pool.submit(format_linked_issue, client, linked_key, link_desc): linked_key
                for link_desc, _direction, linked_key in linked
            }
            for future in as_completed(futures):
                results[futures[future]] = future.result()
        # Preserve original order
        for _link_desc, _direction, linked_key in linked:
            if linked_key in results:
                parts.append(results[linked_key])
                parts.append("")

    print("\n".join(parts))


if __name__ == "__main__":
    main()
