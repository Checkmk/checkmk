#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Post-process Bazel rust_test XML output into proper per-test JUnit XML.

Bazel's rust_test targets produce test.xml files where all tests are lumped
into a single <testcase> with raw libtest output in CDATA, and the suite name
contains a random temp dir ID (e.g. test-713312421) that changes each run.

This script scans bazel-testlogs/, detects Rust test XML by the libtest
"running N tests" marker, parses individual test results, and writes one
test.xml per Rust target into a parallel output directory, with stable suite
names and one <testcase> per Rust test.

Usage:
    bazel --run_under="cd $PWD &&" run //buildscripts/scripts:collect_rust_tests \
        -- $(bazel info bazel-testlogs) results/unit
"""

import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape

RUNNING_RE = re.compile(r"^running \d+ tests?$")
TEST_LINE_RE = re.compile(r"^test (?P<name>\S+) \.\.\. (?P<status>ok|FAILED|ignored)$")
FAILURE_HEADER_RE = re.compile(r"^---- (?P<name>.+) stdout ----$")
RANDOM_DIR_RE = re.compile(r"/test-\d+/")


def stable_target_name(xml_path: Path, testlogs_root: Path) -> str:
    """Derive a stable Bazel target name from the test.xml path.

    Strips the random temp-dir component (test-XXXXXXX) inserted by Bazel's
    Rust test runner, e.g.:
      tests/packaging/package_validator/test-713312421/unit_tests/test.xml
      → tests/packaging/package_validator/unit_tests
    """
    rel = xml_path.parent.relative_to(testlogs_root).as_posix()
    return RANDOM_DIR_RE.sub("/", rel).strip("/")


def extract_cdata(xml_path: Path) -> str | None:
    """Return the text content of <system-out> in the test.xml, or None."""
    try:
        tree = ET.parse(xml_path)
    except ET.ParseError:
        return None
    node = tree.find(".//system-out")
    if node is None or not node.text:
        return None
    return node.text


def parse_failure_blocks(lines: list[str]) -> dict[str, str]:
    """Parse the failures: section and return {test_name: output_text}."""
    failures: dict[str, str] = {}
    current_name: str | None = None
    current_lines: list[str] = []
    in_failures = False

    for line in lines:
        if line.rstrip() == "failures:":
            if current_name is not None:
                failures[current_name] = "".join(current_lines).strip()
                current_name = None
                current_lines = []
            in_failures = True
            continue

        if not in_failures:
            continue

        m = FAILURE_HEADER_RE.match(line.rstrip())
        if m:
            if current_name is not None:
                failures[current_name] = "".join(current_lines).strip()
            current_name = m.group("name")
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        failures[current_name] = "".join(current_lines).strip()

    return failures


def parse_libtest_output(cdata: str) -> tuple[list[tuple[str, str]], dict[str, str]] | None:
    """Parse libtest output from CDATA text.

    Returns (test_results, failure_outputs) where:
      test_results = [(name, status), ...] with status in ok/FAILED/ignored
      failure_outputs = {name: output_text}

    Returns None if no libtest output is found (not a Rust test).
    """
    lines = cdata.splitlines(keepends=True)

    # Find the start of libtest output ("running N tests")
    start = None
    for i, line in enumerate(lines):
        if RUNNING_RE.match(line.strip()):
            start = i
            break

    if start is None:
        return None

    libtest_lines = lines[start:]
    test_results: list[tuple[str, str]] = []

    for line in libtest_lines:
        m = TEST_LINE_RE.match(line.strip())
        if m:
            test_results.append((m.group("name"), m.group("status")))

    failure_outputs = parse_failure_blocks(libtest_lines)
    return test_results, failure_outputs


def make_testsuite(
    target_name: str,
    test_results: list[tuple[str, str]],
    failure_outputs: dict[str, str],
) -> ET.Element:
    """Build a <testsuite> element with one <testcase> per Rust test."""
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

    if not test_results:
        ET.SubElement(suite, "testcase", {"name": "no tests"})
        suite.set("tests", "1")
        return suite

    tests = failures = skipped = 0

    for name, status in test_results:
        tests += 1
        parts = name.rsplit("::", 1)
        classname = parts[0] if len(parts) > 1 else target_name
        tc = ET.SubElement(
            suite,
            "testcase",
            {"classname": escape(classname), "name": escape(name), "time": "0"},
        )
        if status == "FAILED":
            failures += 1
            output = failure_outputs.get(name, "Test failed (no output captured)")
            failure_el = ET.SubElement(
                tc, "failure", {"type": "test failure", "message": escape(name)}
            )
            failure_el.text = escape(output)
        elif status == "ignored":
            skipped += 1
            ET.SubElement(tc, "skipped")

    suite.set("tests", str(tests))
    suite.set("failures", str(failures))
    suite.set("skipped", str(skipped))
    return suite


def write_rust_suites(testlogs_root: Path, output_dir: Path) -> None:
    """Write one test.xml per Rust target under output_dir, preserving target structure."""
    for xml_path in sorted(testlogs_root.rglob("test.xml")):
        cdata = extract_cdata(xml_path)
        if cdata is None:
            continue

        parsed = parse_libtest_output(cdata)
        if parsed is None:
            continue  # not a Rust test

        test_results, failure_outputs = parsed
        target_name = stable_target_name(xml_path, testlogs_root)
        suite = make_testsuite(target_name, test_results, failure_outputs)

        testsuites = ET.Element(
            "testsuites",
            {
                "tests": suite.get("tests", "0"),
                "failures": suite.get("failures", "0"),
            },
        )
        testsuites.append(suite)

        out_path = output_dir / target_name / "test.xml"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            testsuites, encoding="unicode"
        )
        out_path.write_text(xml, encoding="utf-8")
        sys.stderr.write(f"wrote {out_path}\n")


def main() -> None:
    if len(sys.argv) != 3:
        sys.stderr.write("usage: collect_rust_tests.py <bazel-testlogs> <output-dir>\n")
        sys.exit(2)

    testlogs_root = Path(sys.argv[1]).resolve()
    output_dir = Path(sys.argv[2]).resolve()

    if not testlogs_root.is_dir():
        sys.stderr.write(f"error: not a directory: {testlogs_root}\n")
        sys.exit(2)

    output_dir.mkdir(parents=True, exist_ok=True)
    write_rust_suites(testlogs_root, output_dir)


if __name__ == "__main__":
    main()
