#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# The script parses an LCOV coverage data file and generates a CSV summary of line and function coverage per file.

import argparse
import csv
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class CoverageStats:
    """Line and function coverage of a module or the whole repo, with percentages."""

    lines_coverage_percent: float
    functions_coverage_percent: float
    covered_lines: int
    total_lines: int
    covered_functions: int
    total_functions: int


@dataclass(frozen=True, kw_only=True)
class RawStats:
    """Covered and total line/function counts read off an LCOV tracefile."""

    lines: int = 0
    lines_covered: int = 0
    functions: int = 0
    functions_covered: int = 0


@dataclass
class _FileTally:
    """What one file's records say, before it becomes a :class:`RawStats`.

    Lines are kept per line number so a line counts once however many records
    mention it. Nothing in this pipeline writes a file twice, but these counts
    are what the dashboard publishes and should not depend on that staying true.

    Function records are kept as a list and not keyed by name: a closure defined
    in both branches of an if/else has one qualified name and two definitions.
    """

    line_hits: dict[int, int] = field(default_factory=dict)
    function_hits: list[int] = field(default_factory=list)

    def record_line(self, *, lineno: int, hits: int) -> None:
        self.line_hits[lineno] = max(self.line_hits.get(lineno, 0), hits)

    def record_function(self, *, hits: int) -> None:
        self.function_hits.append(hits)

    def stats(self) -> RawStats:
        return RawStats(
            lines=len(self.line_hits),
            lines_covered=sum(hits > 0 for hits in self.line_hits.values()),
            functions=len(self.function_hits),
            functions_covered=sum(hits > 0 for hits in self.function_hits),
        )


def parse_lcov(lines: Iterable[str]) -> dict[str, RawStats]:
    """Aggregate per-file line and function coverage from LCOV tracefile lines.

    Line coverage comes from ``DA:<line>,<hits>``, spelled alike in both
    tracefile generations. Function coverage has two spellings, and which appears
    depends on which step wrote the record:

    * ``FNDA:<hits>,<name>`` -- lcov 1.x, as Bazel's ``--combined_report=lcov``
      writes the measured records.
    * ``FNA:<index>,<hits>,<name>`` -- lcov 2.x, as :mod:`scope` writes the
      zero-coverage records it appends.

    Both are accepted so a file is counted the same either way; a single file's
    records only ever use one, being either measured or synthesised. The
    ``FNL:``/``FN:`` declarations carry no hit count and are ignored.
    """
    tallies: dict[str, _FileTally] = defaultdict(_FileTally)

    current_file: str | None = None
    for raw_line in lines:
        line = raw_line.strip()
        if line.startswith("SF:"):
            current_file = line[3:]
        elif current_file is None:
            continue
        elif line.startswith("FNA:"):
            tallies[current_file].record_function(hits=int(line[4:].split(",", 2)[1]))
        elif line.startswith("FNDA:"):
            tallies[current_file].record_function(hits=int(line[5:].split(",", 1)[0]))
        elif line.startswith("DA:"):
            lineno, hits = line[3:].split(",")[:2]
            tallies[current_file].record_line(lineno=int(lineno), hits=int(hits))
    return {path: tally.stats() for path, tally in tallies.items()}


def calculate_coverage_stats(stats: RawStats) -> CoverageStats:
    """Calculate coverage percentages for given stats."""
    line_cov_pct = 100.0 * stats.lines_covered / stats.lines if stats.lines else 0
    func_cov_pct = 100.0 * stats.functions_covered / stats.functions if stats.functions else 0

    return CoverageStats(
        lines_coverage_percent=round(line_cov_pct, 2),
        functions_coverage_percent=round(func_cov_pct, 2),
        covered_lines=stats.lines_covered,
        total_lines=stats.lines,
        covered_functions=stats.functions_covered,
        total_functions=stats.functions,
    )


def calculate_total_coverage(file_data: dict[str, RawStats]) -> CoverageStats:
    """Calculate total project coverage statistics."""
    stats = file_data.values()
    return calculate_coverage_stats(
        RawStats(
            lines=sum(s.lines for s in stats),
            lines_covered=sum(s.lines_covered for s in stats),
            functions=sum(s.functions for s in stats),
            functions_covered=sum(s.functions_covered for s in stats),
        )
    )


def write_csv_row(writer: csv.DictWriter[str], file_path: str, stats: CoverageStats) -> None:
    """Write a single coverage row to CSV."""
    writer.writerow({"file_path": file_path, **asdict(stats)})


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
