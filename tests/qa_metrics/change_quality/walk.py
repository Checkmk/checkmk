#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Walk git history once and stream every commit that added a werk file.

Replaces the per-werk fan-out in the previous ``resolve`` module: instead of
asking "which commit added werk X?" for every werk, we ask git "what commits
on HEAD ever added a ``.werks/<id>`` path?" in a single ``git log`` invocation
and stream the answers. The commit's full files-changed list is included for
free, so callers can compute ``has_test`` / ``source_component`` without
further git calls.
"""

from __future__ import annotations

import logging
import re
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, UTC
from pathlib import Path

logger = logging.getLogger(__name__)

_CHANGE_ID = re.compile(r"^Change-Id:\s*(I[0-9a-f]+)\s*$", re.MULTILINE | re.IGNORECASE)
_WERK_PATH = re.compile(r"^\.werks/(\d+)(\.md)?$")

# `%B` can contain blank lines and arbitrary user text. Use ASCII NUL as a
# field separator: it is forbidden in git refs and paths, and rejected by
# every commit-message tool, so it can never appear in the data we parse.
# The literal ``CSTART`` / ``CEND`` words bracketing the NULs make the
# boundaries human-readable in error messages.
_COMMIT_START = "\x00CSTART\x00"
_BODY_END = "\x00CEND"
_FMT = "%x00CSTART%x00%H%x00%ae%x00%ct%x00%s%x00%B%x00CEND"


@dataclass(frozen=True)
class CommitInfo:
    sha: str
    author_email: str
    subject: str
    commit_time: datetime
    gerrit_change_id: str | None
    files_changed: tuple[str, ...]


@dataclass(frozen=True)
class WerkAdd:
    werk_id: int
    commit: CommitInfo


def walk_werk_adds(
    repo: Path,
    *,
    since: date | None = None,
    until: date | None = None,
) -> Iterator[WerkAdd]:
    """Stream every non-merge commit on HEAD that added a ``.werks/<id>`` file.

    Yields one ``WerkAdd`` per added werk file (a single commit can add
    multiple werks → multiple events with the same ``commit``).
    """
    args = [
        "git",
        "log",
        # Walk oldest-first so emitted rows follow commit-creation order:
        # an incremental re-run that picks up one new commit appends a row
        # at the end rather than prepending to the natural ordering.
        "--reverse",
        "--no-renames",
        "--no-merges",
        "--name-status",
        f"--format={_FMT}",
    ]
    if since is not None:
        args.append(f"--since={since.isoformat()}")
    if until is not None:
        args.append(f"--until={until.isoformat()}")
    args.append("HEAD")

    proc = subprocess.run(args, cwd=repo, capture_output=True, text=True, check=True)
    yield from _parse(proc.stdout)


def _parse(out: str) -> Iterator[WerkAdd]:
    # First chunk before the first sentinel is empty / git preamble.
    for chunk in out.split(_COMMIT_START)[1:]:
        commit, werk_ids = _parse_chunk(chunk)
        for werk_id in werk_ids:
            yield WerkAdd(werk_id=werk_id, commit=commit)


def _parse_chunk(chunk: str) -> tuple[CommitInfo, list[int]]:
    # chunk = "<sha>\x00<ae>\x00<ct>\x00<subject>\x00<body>\x00CEND\n<files>\n\n"
    fields, sep, files_blob = chunk.partition(_BODY_END)
    if not sep:
        raise ValueError(f"malformed git-log chunk (no body terminator): {chunk[:200]!r}")
    parts = fields.split("\x00")
    if len(parts) != 5:
        raise ValueError(
            f"malformed git-log chunk (expected 5 NUL-separated fields, got {len(parts)}): "
            f"{chunk[:200]!r}"
        )
    sha, author_email, ct, subject, body = parts

    all_files: list[str] = []
    werk_ids: list[int] = []
    for line in files_blob.splitlines():
        if not line.strip() or "\t" not in line:
            continue
        status, _, path = line.partition("\t")
        all_files.append(path)
        if status == "A" and (m := _WERK_PATH.match(path)) is not None:
            werk_ids.append(int(m.group(1)))

    change_id_match = _CHANGE_ID.search(body)
    info = CommitInfo(
        sha=sha,
        author_email=author_email,
        subject=subject,
        commit_time=datetime.fromtimestamp(int(ct), tz=UTC),
        gerrit_change_id=change_id_match.group(1) if change_id_match else None,
        files_changed=tuple(all_files),
    )
    return info, werk_ids
