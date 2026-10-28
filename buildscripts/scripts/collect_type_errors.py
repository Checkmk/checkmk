#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import posixpath
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from itertools import chain
from pathlib import Path


@dataclass(frozen=True)
class TypeErrorLine:
    file: str
    line: int
    column: int
    kind: str
    message: str


MYPY_ERROR_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):(?P<column>\d+): (?P<kind>error|note|warning): (?P<msg>.*)$"
)

TSC_ERROR_RE = re.compile(
    r"^(?:(?P<file>.+)\((?P<line>\d+),(?P<column>\d+)\): )?(?P<kind>error|warning|message) (?P<msg>TS\d+: .*)$"
)

MYPY_SUFFIX = ".mypy_stdout"

VUE_TSC_SUFFIX = "_vue_tsc.log"


def parse_mypy_output(lines: Iterable[str]) -> Iterator[TypeErrorLine]:
    """Parse mypy output"""
    for line in lines:
        m = MYPY_ERROR_RE.match(line)
        if m:
            yield TypeErrorLine(
                file=m.group("file"),
                line=int(m.group("line")),
                column=int(m.group("column")),
                kind=m.group("kind"),
                message=m.group("msg"),
            )


def parse_tsc_output(lines: Iterable[str], package: str) -> Iterator[TypeErrorLine]:
    """Parse vue-tsc output, whose paths are relative to the package and
    whose diagnostics of the whole project have no location"""
    error: TypeErrorLine | None = None
    for line in lines:
        if error and line.startswith(" "):
            error = replace(error, message=f"{error.message}\n{line}")
            continue
        if error:
            yield error
            error = None
        if m := TSC_ERROR_RE.match(line):
            error = TypeErrorLine(
                file=posixpath.normpath(posixpath.join(package, m.group("file") or "")),
                line=int(m.group("line") or 0),
                column=int(m.group("column") or 0),
                kind=m.group("kind"),
                message=m.group("msg"),
            )
    if error:
        yield error


def target_name_from_path(path: Path, bin_root: Path, suffix: str) -> str:
    """Strip bin_root and suffix."""
    assert path.name.endswith(suffix)
    return path.relative_to(bin_root).as_posix()[: -len(suffix)]


def errors_per_target(bin_root: Path) -> Iterator[tuple[str, Iterator[TypeErrorLine]]]:
    for path in sorted(
        p for p in bin_root.rglob("*") if p.name.endswith((MYPY_SUFFIX, VUE_TSC_SUFFIX))
    ):
        lines = path.read_text(errors="replace").splitlines()
        if path.name.endswith(MYPY_SUFFIX):
            yield target_name_from_path(path, bin_root, MYPY_SUFFIX), parse_mypy_output(lines)
        else:
            yield (
                target_name_from_path(path, bin_root, VUE_TSC_SUFFIX),
                parse_tsc_output(lines, path.parent.relative_to(bin_root).as_posix()),
            )


def make_testsuite(
    target_name: str, errors: Iterator[TypeErrorLine]
) -> tuple[ET.Element, int, int]:
    """
    Create one <testsuite> per Bazel target, with per-error testcases.
    """
    suite = ET.Element(
        "testsuite",
        {
            "name": target_name,
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
                    "message": error.message,
                },
            )
            failure.text = f"{error.file}:{error.line}:{error.column}: {error.message}"

    suite.set("tests", str(tests))
    suite.set("failures", str(failures))
    return suite, tests, failures


def main() -> None:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: collect_type_errors.py <bazel-out/k8-fastbuild/bin>\n")
        sys.exit(2)

    bin_root = Path(sys.argv[1]).resolve()
    if not bin_root.is_dir():
        sys.stderr.write(f"error: not a directory: {bin_root}\n")
        sys.exit(2)

    testsuites = ET.Element("testsuites")
    total_tests = 0
    total_failures = 0

    for target, errors in errors_per_target(bin_root):
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
