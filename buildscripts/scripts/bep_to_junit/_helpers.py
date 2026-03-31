# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Shared helpers: URI reading, label/filename conversion, XML writing."""

from __future__ import annotations

import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

MAX_LOG_BYTES = 16_000  # cap log body per failure to keep XML manageable


def read_uri(uri: str) -> str:
    """Return text content of a file:// URI; empty string on any error."""
    if not uri.startswith("file://"):
        return ""
    try:
        return Path(urlparse(uri).path).read_text(errors="replace")
    except OSError:
        return ""


def label_to_dirname(label: str) -> str:
    """//foo/bar:baz_test  →  foo_bar_baz_test"""
    return re.sub(r"[^a-zA-Z0-9_]", "_", label.lstrip("/"))


def label_to_classname(label: str) -> str:
    """//foo/bar:baz_test  →  foo.bar"""
    return label.lstrip("/").split(":", 1)[0].replace("/", ".")


def label_to_name(label: str) -> str:
    """//foo/bar:baz_test  →  baz_test"""
    return label.split(":", 1)[1] if ":" in label else label.lstrip("/")


def action_duration_seconds(start: str, end: str) -> float:
    """Return wall-clock seconds between two ISO 8601 timestamps, or 0.0 on error."""

    def _parse(ts: str) -> float | None:
        try:
            return datetime.fromisoformat(
                re.sub(r"(\.\d{6})\d*", r"\1", ts).replace("Z", "+00:00")
            ).timestamp()
        except ValueError:
            return None

    t_start, t_end = _parse(start), _parse(end)
    return max(0.0, t_end - t_start) if t_start is not None and t_end is not None else 0.0


def write_xml(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"
    )
    print(f"wrote {path}", file=sys.stderr)


def make_xml(
    label: str, error_message: str, log_content: str, time_seconds: float = 0.0
) -> ET.Element:
    """Build a single-testcase JUnit XML tree."""
    root = ET.Element("testsuites", tests="1", errors="1", failures="0")
    suite = ET.SubElement(root, "testsuite", name=label, tests="1", errors="1", failures="0")
    testcase = ET.SubElement(
        suite,
        "testcase",
        classname=label_to_classname(label),
        name=label_to_name(label),
        time=f"{time_seconds:.3f}",
    )
    summary = error_message.split("\n", maxsplit=1)[0][:200]
    error_el = ET.SubElement(testcase, "error", message=summary, type="Error")
    error_el.text = error_message
    if log_content:
        ET.SubElement(suite, "system-out").text = log_content[:MAX_LOG_BYTES]
    return root
