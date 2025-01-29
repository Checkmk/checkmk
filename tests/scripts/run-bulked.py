#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import argparse
import datetime
import logging
import os
import sys

# Make the tests.testlib available
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tests.testlib.repo import repo_path
from tests.testlib.utils import run

logger = logging.getLogger("pytest-bulked")


def _parse_args() -> tuple[argparse.Namespace, list[str]]:
    """Register known arguments, parse and return known and unknown arguments."""
    parser = argparse.ArgumentParser(description="Return a string.")
    parser.add_argument(dest="test_path")
    parser.add_argument("-T", dest="test_type", default="unit")
    parser.add_argument("-k", dest="filter_expression", default=None)
    parser.add_argument("--chunk-size", dest="chunk_size", type=int, default=100)
    parser.add_argument("--chunk-index", dest="chunk_index", type=int, default=None)
    parser.add_argument("--log-level", dest="log_level", default="INFO")
    return parser.parse_known_args()


def main() -> None:
    args, unknown_args = _parse_args()
    unknown_args = [_ for _ in unknown_args if _ != "--bulk-mode"]
    logging.basicConfig(level=args.log_level)

    report_suffix = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    report_file = f"./junit.{report_suffix}.xml"

    pytest_cmd = ["pytest", "-T", args.test_type, args.test_path, "--bulk-mode"] + unknown_args
    if args.filter_expression:
        pytest_cmd.append("-k")
        pytest_cmd.append(args.filter_expression)

    collection_stats = (
        run(pytest_cmd + ["--collect-only"]).stdout.split("\ncollected ", 1)[-1].split("\n", 1)[0]
    )
    logger.info("Collected %s", collection_stats)
    test_count = [int(_) for _ in collection_stats.split(" ") if _.isnumeric()][-1]
    logger.info("Active tests: %s", test_count)

    if args.chunk_index:
        chunks = [args.chunk_index]
    else:
        chunks = [
            *range(0, (test_count // args.chunk_size) + int(bool(test_count % args.chunk_size)))
        ]

    logger.info("Chunk size: %s", args.chunk_size)
    logger.info("Chunk count: %s", len(chunks))

    chunk_reports: list[str] = []
    for chunk_index in chunks:
        chunk_reports.append(f"/tmp/~junit.{report_suffix}.chunk{chunk_index}.xml")
        run(
            pytest_cmd
            + [
                f"--chunk-index={chunk_index}",
                f"--chunk-size={args.chunk_size}",
                f"--junitxml={chunk_reports[-1]}",
            ],
            check=False,
        )

    # merge chunk reports
    run(
        [f"{repo_path()}/tests/scripts/merge-junit-suites.py"]
        + chunk_reports
        + [report_file, "--stats", f"--pytest-suite-name={args.test_type}"]
    )
    for chunk_report in chunk_reports:
        os.remove(chunk_report)

    # generate HTML report
    run(["junit2html", report_file, f"{report_file.removesuffix('.xml')}.htm"], check=False)


if __name__ == "__main__":
    main()
