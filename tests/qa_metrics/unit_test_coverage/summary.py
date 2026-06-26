#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The script parses an LCOV coverage data file and generates a CSV summary of line and function coverage per file.

import argparse
import csv
from collections import defaultdict
from collections.abc import Iterable
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


def _record_line(stats: RawStats, *, hits: int) -> None:
    stats["lines"] += 1
    if hits > 0:
        stats["lines_covered"] += 1


def _record_function(stats: RawStats, *, hits: int) -> None:
    stats["functions"] += 1
    if hits > 0:
        stats["functions_covered"] += 1


def parse_lcov(lines: Iterable[str]) -> dict[str, RawStats]:
    """Aggregate per-file line and function coverage from LCOV tracefile lines.

    The tracefile is lcov 2.x, as emitted by the ``lcov`` filtering step that
    feeds this parser. Function coverage comes from the
    ``FNA:<index>,<hits>,<name>`` data records (the ``FNL:`` declarations carry
    no hit count and are ignored); line coverage from ``DA:<line>,<hits>``
    records.
    """
    file_data: dict[str, RawStats] = defaultdict(
        lambda: RawStats(lines=0, lines_covered=0, functions=0, functions_covered=0)
    )

    current_file: str | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("SF:"):
            current_file = line[3:]
        elif current_file is None:
            continue
        elif line.startswith("FNA:"):
            _record_function(file_data[current_file], hits=int(line[4:].split(",", 2)[1]))
        elif line.startswith("DA:"):
            _record_line(file_data[current_file], hits=int(line[3:].split(",")[1]))
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

    with Path(args.lcov_file).open(encoding="utf-8") as lcov_file:
        file_data = parse_lcov(lcov_file)
    output_csv = Path(args.csv_output)

    write_csv(file_data, output_csv, total_only=args.total_only)

    output_type = "Total" if args.total_only else "Detailed"
    print(f"{output_type} coverage CSV summary written to {args.csv_output}")


if __name__ == "__main__":
    main()
