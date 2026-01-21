#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from itertools import chain
from pathlib import Path
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class MypyErrorLine:
    file: str
    line: int
    column: int
    kind: str
    message: str


MYPY_ERROR_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+): (?P<kind>error|note|warning): (?P<msg>.*)$"
)

STDOUT_SUFFIX: int = ".mypy_stdout"


def parse_mypy_output(lines: Iterable[str]) -> Iterator[MypyErrorLine]:
    """Parse mypy output"""
    for line in lines:
        m = MYPY_ERROR_RE.match(line)
        if m:
            yield MypyErrorLine(
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("column")),
                kind=m.group("kind"),
                message=m.group("msg"),
            )


def target_name_from_path(path: Path, bin_root: Path) -> str:
    """Strip bin_root and extension."""
    assert path.name.endswith(STDOUT_SUFFIX)
    return path.relative_to(bin_root).as_posix()[: -len(STDOUT_SUFFIX)]


def make_testsuite(
    target_name: str, errors: Iterator[MypyErrorLine]
) -> tuple[ET.Element, int, int]:
    """
    Create one <testsuite> per Bazel target, with per-error testcases.
    """
    suite = ET.Element(
        "testsuite",
        {
            "name": escape(target_name),
            "tests": "0",
            "failures": "0",
            "errors": "0",
            "skipped": "0",
        },
    )

    tests = 0
    failures = 0

    try:
        first = next(errors)
    except StopIteration:
        ET.SubElement(
            suite,
            "testcase",
            {
                "classname": target_name,
                "name": "no errors",
            },
        )
        tests = 1
    else:
        for error in chain([first], errors):
            tests += 1
            failures += 1
            tc = ET.SubElement(
                suite,
                "testcase",
                {
                    "classname": target_name,
                    "name": f"{error.file}:{error.line}:{error.column}:{error.kind}",
                },
            )
            failure = ET.SubElement(
                tc,
                "failure",
                {
                    "type": error.kind,
                    "message": escape(error.message),
                },
            )
            failure.text = escape(f"{error.file}:{error.line}:{error.column}: {error.message}")

    suite.set("tests", str(tests))
    suite.set("failures", str(failures))
    return suite, tests, failures


def main() -> None:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: mypy2junit.py <bazel-out/k8-fastbuild/bin>\n")
        sys.exit(2)

    bin_root = Path(sys.argv[1]).resolve()
    if not bin_root.is_dir():
        sys.stderr.write(f"error: not a directory: {bin_root}\n")
        sys.exit(2)

    testsuites = ET.Element("testsuites")
    total_tests = 0
    total_failures = 0

    stdout_files = sorted(bin_root.rglob(f"*{STDOUT_SUFFIX}"))

    for path in stdout_files:
        with path.open(errors="replace") as f:
            errors = parse_mypy_output(f.readlines())
        target = target_name_from_path(path, bin_root)
        suite, tests, failures = make_testsuite(target, errors)
        testsuites.append(suite)
        total_tests += tests
        total_failures += failures

    testsuites.set("tests", str(total_tests))
    testsuites.set("failures", str(total_failures))

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(testsuites, encoding="unicode")
    sys.stdout.write(xml)


if __name__ == "__main__":
    main()
