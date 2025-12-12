#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""
Coverage Maintenance Script

Assists in maintaining coverage tracing of unit tests by managing tests marked
with @pytest.mark.skip_on_code_coverage.

Some tests fail when run with coverage instrumentation. The 'test-unit-all-coverage'
make target skips these tests by passing '-m "not skip_on_code_coverage"' to pytest.

Related make targets:
    - test-unit-all: Run all unit tests without coverage
    - test-unit-all-coverage: Run unit tests with coverage (skips marked tests)

Use --help for usage information.
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass
class TestInfo:
    """Information about a test."""

    file_path: Path
    test_name: str
    line_number: int | None = None
    has_skip_marker: bool = False


@dataclass
class TestResult:
    """Result of a test run."""

    test_id: str
    status: Literal["passed", "failed", "skipped", "error"]
    file_path: str
    test_name: str


class CoverageMaintenanceAnalyzer:
    """Analyzer for coverage test maintenance."""

    SKIP_MARKER = "@pytest.mark.skip_on_code_coverage"
    REPO_ROOT = Path(__file__).resolve().parents[2]
    TESTS_DIR = REPO_ROOT / "tests"

    def log(self, message: str, level: str = "info") -> None:
        """Log a message if verbose mode is enabled."""
        if level == "error":
            prefix = {"info": "[INFO]", "warning": "[WARN]", "error": "[ERROR]"}[level]
            print(f"{prefix} {message}", file=sys.stderr if level == "error" else sys.stdout)

    def find_skipped_tests(self) -> list[TestInfo]:
        """Find all tests with skip_on_code_coverage marker."""
        skipped_tests = []

        # Use grep to find all files with the marker
        try:
            result = subprocess.run(
                [
                    "grep",
                    "-r",
                    "-n",
                    "--include=*.py",
                    self.SKIP_MARKER,
                    str(self.TESTS_DIR / "unit"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            for line in result.stdout.splitlines():
                if not line.strip():
                    continue

                line_match = re.match(r"([^:]+):(\d+):(.*)", line)
                if not line_match:
                    continue

                file_path_str, line_num, _ = line_match.groups()
                file_path = Path(file_path_str)

                # Extract test function name from the next lines
                test_name = self._extract_test_name_at_line(file_path, int(line_num))
                if test_name:
                    skipped_tests.append(
                        TestInfo(
                            file_path=file_path,
                            test_name=test_name,
                            line_number=int(line_num),
                            has_skip_marker=True,
                        )
                    )

        except Exception as e:
            self.log(f"Error searching for skipped tests: {e}", "error")

        return skipped_tests

    def _extract_test_name_at_line(self, file_path: Path, line_number: int) -> str | None:
        """Extract the test function name after a given line number."""
        try:
            with open(file_path, encoding="utf-8") as f:
                lines = f.readlines()

            # Look for the next function definition after the marker
            for i in range(line_number, min(line_number + 5, len(lines))):
                line = lines[i].strip()
                if line.startswith("def test_"):
                    func_match = re.match(r"def (test_\w+)", line)
                    if func_match:
                        return func_match.group(1)
                elif line.startswith("async def test_"):
                    func_match = re.match(r"async def (test_\w+)", line)
                    if func_match:
                        return func_match.group(1)

        except Exception as e:
            self.log(f"Error reading {file_path}: {e}", "warning")

        return None

    def run_coverage_tests(self, dry_run: bool = False) -> list[TestResult]:
        """Run the coverage tests and collect results."""
        if dry_run:
            return []

        test_results = []
        try:
            # Run make target for coverage tests
            subprocess.run(
                ["make", "-C", "tests", "test-unit-all-coverage"],
                cwd=self.REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            # After running, get results from test logs
            test_results = self.get_test_results_from_logs()

        except Exception as e:
            self.log(f"Error running coverage tests: {e}", "error")

        return test_results

    def get_test_results_from_logs(self) -> list[TestResult]:
        """Get test results from bazel test logs."""
        test_results: list[TestResult] = []

        testlogs_dir = self.REPO_ROOT / "bazel-testlogs" / "tests" / "unit"
        if not testlogs_dir.exists():
            return test_results

        # Look for test.xml files
        for xml_file in testlogs_dir.rglob("test.xml"):
            try:
                test_results.extend(self._parse_junit_xml(xml_file))
            except Exception as e:
                self.log(f"Error parsing {xml_file}: {e}", "error")

        return test_results

    def _parse_junit_xml(self, xml_file: Path) -> list[TestResult]:
        """Parse JUnit XML file to extract test results."""
        import xml.etree.ElementTree as ET

        test_results = []

        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for testcase in root.findall(".//testcase"):
                test_name = testcase.get("name", "")
                classname = testcase.get("classname", "")
                file_path = testcase.get("file", "")

                # Determine status
                status: Literal["passed", "failed", "skipped", "error"]
                if testcase.find("failure") is not None:
                    status = "failed"
                elif testcase.find("error") is not None:
                    status = "error"
                elif testcase.find("skipped") is not None:
                    status = "skipped"
                else:
                    status = "passed"

                test_results.append(
                    TestResult(
                        test_id=f"{classname}::{test_name}",
                        status=status,
                        file_path=file_path,
                        test_name=test_name,
                    )
                )

        except Exception as e:
            self.log(f"Error parsing XML file {xml_file}: {e}", "error")

        return test_results

    def find_tests_failing_in_coverage(
        self, test_results: list[TestResult], skipped_tests: list[TestInfo]
    ) -> list[TestResult]:
        """Find tests that fail in coverage run but are not yet skipped."""
        skipped_test_names = {t.test_name for t in skipped_tests}

        failing_not_skipped = [
            result
            for result in test_results
            if result.status in ["failed", "error"] and result.test_name not in skipped_test_names
        ]

        return failing_not_skipped

    def find_tests_passing_but_skipped(
        self, test_results: list[TestResult], skipped_tests: list[TestInfo]
    ) -> list[TestInfo]:
        """Find tests that don't fail anymore but are currently skipped."""
        # Create a mapping of test names to their results
        test_results_map = {result.test_name: result for result in test_results}

        passing_but_skipped = []
        for skipped_test in skipped_tests:
            result = test_results_map.get(skipped_test.test_name)
            # If the test was run and passed, it's a candidate for un-skipping
            # Note: skipped tests won't appear in results if they were actually skipped
            if result and result.status == "passed":
                passing_but_skipped.append(skipped_test)

        return passing_but_skipped

    def get_component_for_file(self, file_path: Path) -> str | None:
        """Get the component name for a file using cmk-components command."""
        try:
            # Use relative path from repo root
            rel_path = file_path.relative_to(self.REPO_ROOT)

            result = subprocess.run(
                ["cmk-components", "component-for", str(rel_path)],
                cwd=self.REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return None

            component = result.stdout.strip()
            return component if component else None

        except FileNotFoundError:
            # cmk-components not found
            return None
        except Exception as e:
            self.log(f"Error getting component for {file_path}: {e}", "error")
            return None

    def get_component_owners(self, component: str) -> list[str]:
        """Get owners for a component using cmk-components command."""
        try:
            result = subprocess.run(
                ["cmk-components", "members", component],
                cwd=self.REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                return []

            # Parse the output using regex to extract owners
            # Look for 'owners': [...] section
            match = re.search(r"'owners':\s*\[(.*?)\]", result.stdout, re.DOTALL)
            if not match:
                return []

            owners_section = match.group(1)
            # Extract email addresses from strings like 'email@example.com  # comment'
            emails = re.findall(r"'([^']*@checkmk\.com)", owners_section)

            # Remove comments after email addresses
            return [email.split("#")[0].strip() for email in emails]

        except FileNotFoundError:
            # cmk-components not found
            return []
        except Exception as e:
            self.log(f"Error getting owners for component {component}: {e}", "error")
            return []

    def group_tests_by_component(self, tests: list[TestInfo]) -> dict[str | None, list[TestInfo]]:
        """Group tests by their component."""
        from collections import defaultdict

        grouped: dict[str | None, list[TestInfo]] = defaultdict(list)

        for test in tests:
            component = self.get_component_for_file(test.file_path)
            grouped[component].append(test)

        return dict(grouped)

    def format_test_info(self, test_info: TestInfo) -> str:
        """Format test information for display."""
        rel_path = test_info.file_path.relative_to(self.REPO_ROOT)
        if test_info.line_number:
            return f"{rel_path}:{test_info.line_number} - {test_info.test_name}"
        else:
            return f"{rel_path} - {test_info.test_name}"

    def format_test_result(self, result: TestResult) -> str:
        """Format test result for display."""
        return f"{result.file_path} - {result.test_name} [{result.status.upper()}]"


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Manage test coverage skip markers (@pytest.mark.skip_on_code_coverage)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            (
                "Workflow:",
                "  1. make -C tests test-unit-all-coverage",
                "  2. %(prog)s --analyze",
                "  3. Add @pytest.mark.skip_on_code_coverage to failing tests",
                "  4. Remove marker from passing tests (if any)",
                "",
                "Examples:",
                "  %(prog)s --list-skipped",
                "  %(prog)s --analyze",
                "  %(prog)s --run-and-analyze",
            )
        ),
    )

    parser.add_argument(
        "--list-skipped",
        action="store_true",
        help="list all tests with skip_on_code_coverage marker",
    )

    parser.add_argument(
        "--find-failing-not-skipped",
        action="store_true",
        help="find tests failing in coverage but not yet skipped",
    )

    parser.add_argument(
        "--find-passing-but-skipped",
        action="store_true",
        help="find tests passing but still marked as skipped",
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="full analysis (list-skipped + find-failing + find-passing)",
    )

    parser.add_argument(
        "--run-and-analyze",
        action="store_true",
        help="run 'make test-unit-all-coverage' then analyze (slow!)",
    )

    parser.add_argument(
        "--components",
        action="store_true",
        help="group tests by component and show component owners (requires cmk-components)",
    )

    args = parser.parse_args()

    # If no action specified, show help
    if not any(
        [
            args.list_skipped,
            args.find_failing_not_skipped,
            args.find_passing_but_skipped,
            args.analyze,
            args.run_and_analyze,
        ]
    ):
        parser.print_help()
        return 0

    analyzer = CoverageMaintenanceAnalyzer()

    # Check if cmk-components is available when --components is used
    if args.components:
        try:
            subprocess.run(
                ["cmk-components", "--version"],
                capture_output=True,
                check=False,
            )
        except FileNotFoundError:
            print(
                "[ERROR] cmk-components not found. Please install zeug_cmk, "
                "add bin to PATH and install uv",
                file=sys.stderr,
            )
            return 1

    # Collect skipped tests
    skipped_tests = analyzer.find_skipped_tests()

    # Collect test results if needed
    test_results = []
    if args.run_and_analyze:
        test_results = analyzer.run_coverage_tests(dry_run=False)
    elif any([args.find_failing_not_skipped, args.find_passing_but_skipped, args.analyze]):
        test_results = analyzer.get_test_results_from_logs()

    # Execute requested actions
    if args.list_skipped or args.analyze:
        print("\n" + "=" * 80)
        print(f"CURRENTLY SKIPPED TESTS: {len(skipped_tests)}")
        print("=" * 80)

        if args.components:
            # Group tests by component and show owners
            grouped = analyzer.group_tests_by_component(skipped_tests)

            for component, tests in sorted(grouped.items(), key=lambda x: x[0] or ""):
                if component:
                    owners = analyzer.get_component_owners(component)
                    owner_str = ", ".join(owners) if owners else "no owners"
                    print(f"\n  Component: {component} [{owner_str}]")
                else:
                    print("\n  Component: unknown [no component info]")

                for test in tests:
                    print(f"    {analyzer.format_test_info(test)}")
        else:
            # Simple list without grouping
            for test in skipped_tests:
                print(f"  {analyzer.format_test_info(test)}")

    if args.find_failing_not_skipped or args.analyze:
        if not test_results:
            print(
                "\n[WARNING] No test results available. "
                "Run coverage tests first or use --run-and-analyze",
                file=sys.stderr,
            )
        else:
            failing_not_skipped = analyzer.find_tests_failing_in_coverage(
                test_results, skipped_tests
            )

            print("\n" + "=" * 80)
            print(f"TESTS FAILING IN COVERAGE (NOT YET SKIPPED): {len(failing_not_skipped)}")
            print("=" * 80)
            if failing_not_skipped:
                print("\n[ACTION REQUIRED] Add @pytest.mark.skip_on_code_coverage to:")
                for result in failing_not_skipped:
                    print(f"  {analyzer.format_test_result(result)}")
            else:
                print("  None found - all failing tests are already skipped!")

    if args.find_passing_but_skipped or args.analyze:
        if not test_results:
            print(
                "\n[WARNING] No test results available. "
                "Run coverage tests first or use --run-and-analyze",
                file=sys.stderr,
            )
        else:
            passing_but_skipped = analyzer.find_tests_passing_but_skipped(
                test_results, skipped_tests
            )

            print("\n" + "=" * 80)
            print(f"TESTS PASSING BUT STILL SKIPPED: {len(passing_but_skipped)}")
            print("=" * 80)
            if passing_but_skipped:
                print(
                    "\n[ACTION RECOMMENDED] Consider removing "
                    "@pytest.mark.skip_on_code_coverage from:"
                )
                for test in passing_but_skipped:
                    print(f"  {analyzer.format_test_info(test)}")
            else:
                print("  None found - all skipped tests are still failing!")

    if args.analyze:
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"  Total tests with skip_on_code_coverage marker: {len(skipped_tests)}")
        if test_results:
            print(f"  Total test results analyzed: {len(test_results)}")
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
