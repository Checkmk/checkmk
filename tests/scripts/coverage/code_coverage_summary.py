#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The script parses an LCOV coverage data file and generates a CSV summary of line and function coverage per file.

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import TypedDict


class CoverageStats(TypedDict):
    """Type definition for coverage statistics."""

    lines_coverage_percent: float
    functions_coverage_percent: float
    covered_lines: int
    total_lines: int
    covered_functions: int
    total_functions: int


class RawStats(TypedDict):
    """Type definition for raw statistics from LCOV parsing."""

    lines: int
    lines_covered: int
    functions: int
    functions_covered: int


def parse_lcov(lcov_file: Path) -> dict[str, RawStats]:
    file_data: dict[str, RawStats] = defaultdict(
        lambda: RawStats(lines=0, lines_covered=0, functions=0, functions_covered=0)
    )

    with open(lcov_file, encoding="utf-8") as f:
        current_file = None
        functions: set[str] = set()
        functions_covered: set[str] = set()

        for line in f:
            line = line.strip()
            if line.startswith("SF:"):
                # New file detected
                current_file = line[3:]
                functions = set()
                functions_covered = set()
            elif line.startswith("FN:"):
                # Function name (start position, functionname)
                parts = line[3:].split(",")
                if len(parts) == 2:
                    functions.add(parts[1])
            elif line.startswith("FNDA:"):
                # Function coverage data (hitcount, functionname)
                parts = line[5:].split(",")
                if len(parts) == 2 and int(parts[0]) > 0:
                    functions_covered.add(parts[1])
            elif line.startswith("DA:") and current_file:
                # Line coverage data (lineno, hitcount)
                parts = line[3:].split(",")
                if len(parts) == 2:
                    file_data[current_file]["lines"] += 1
                    if int(parts[1]) > 0:
                        file_data[current_file]["lines_covered"] += 1
            elif line == "end_of_record" and current_file:
                # Finalize function data for this file
                file_data[current_file]["functions"] += len(functions)
                file_data[current_file]["functions_covered"] += len(functions_covered)
    return file_data


def calculate_coverage_stats(stats: RawStats) -> CoverageStats:
    """Calculate coverage percentages for given stats."""
    total_lines = stats["lines"]
    covered_lines = stats["lines_covered"]
    line_cov_pct = 100.0 * covered_lines / total_lines if total_lines else 0

    total_funcs = stats["functions"]
    covered_funcs = stats["functions_covered"]
    func_cov_pct = 100.0 * covered_funcs / total_funcs if total_funcs else 0

    return CoverageStats(
        lines_coverage_percent=round(line_cov_pct, 2),
        functions_coverage_percent=round(func_cov_pct, 2),
        covered_lines=covered_lines,
        total_lines=total_lines,
        covered_functions=covered_funcs,
        total_functions=total_funcs,
    )


def calculate_total_coverage(file_data: dict[str, RawStats]) -> CoverageStats:
    """Calculate total project coverage statistics."""
    totals = RawStats(lines=0, lines_covered=0, functions=0, functions_covered=0)
    for stats in file_data.values():
        totals["lines"] += stats["lines"]
        totals["lines_covered"] += stats["lines_covered"]
        totals["functions"] += stats["functions"]
        totals["functions_covered"] += stats["functions_covered"]

    return calculate_coverage_stats(totals)


def write_csv_row(writer: csv.DictWriter[str], file_path: str, stats: CoverageStats) -> None:
    """Write a single coverage row to CSV."""
    writer.writerow(
        {
            "file_path": file_path,
            **stats,
        }
    )


def write_csv(
    file_data: dict[str, RawStats], csv_output: Path, *, total_only: bool = False
) -> None:
    """Write coverage data to CSV file."""
    fieldnames = [
        "file_path",
        "lines_coverage_percent",
        "functions_coverage_percent",
        "covered_lines",
        "total_lines",
        "covered_functions",
        "total_functions",
    ]

    with open(csv_output, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        if total_only:
            # Write only total coverage summary
            total_stats = calculate_total_coverage(file_data)
            write_csv_row(writer, "TOTAL", total_stats)
        else:
            # Write per-file coverage data
            for file_path, stats in file_data.items():
                file_stats = calculate_coverage_stats(stats)
                write_csv_row(writer, file_path, file_stats)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse LCOV data file and output coverage summary as CSV"
    )
    parser.add_argument(
        "--lcov-file", "-i", required=True, type=str, help="Path to the LCOV data file"
    )
    parser.add_argument(
        "--csv-output", "-o", required=True, type=str, help="Path to the output CSV file"
    )
    parser.add_argument(
        "--total-only",
        "-t",
        action="store_true",
        help="Output only total project coverage summary (CSV with single TOTAL row)",
    )
    args = parser.parse_args()

    input_lcov = Path(args.lcov_file)
    file_data = parse_lcov(input_lcov)
    output_csv = Path(args.csv_output)

    write_csv(file_data, output_csv, total_only=args.total_only)

    output_type = "Total" if args.total_only else "Detailed"
    print(f"{output_type} coverage CSV summary written to {args.csv_output}")


if __name__ == "__main__":
    main()
