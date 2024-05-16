#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
from pathlib import Path
from pprint import pprint as pp
from typing import Iterator, NamedTuple


class Summary(NamedTuple):
    overallTargets: int
    cacheHits: int
    percentRemoteCacheHits: float
    targetsWithMissedCache: list[str]
    numberUncacheableTargets: int
    numberRemotableTargets: int


# no one needs pydantics BaseModel for the price of a complete venv
class ExecutionMetrics:
    def __init__(self, **kwargs) -> None:
        setattr(self, "targetLabel", "")
        setattr(self, "cacheHit", bool)
        setattr(self, "cacheable", bool)
        setattr(self, "remotable", bool)

        for key, value in kwargs.items():
            if key in ("targetLabel"):
                setattr(self, key, str(value))
            elif key in ("cacheHit", "cacheable", "remotable"):
                setattr(self, key, bool(value))


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--execution_logs_root", default=Path(__file__).resolve().parent.parent.parent, type=Path
    )

    parser.add_argument(
        "--bazel_log_file_pattern",
        default="bazel_execution_log*.json",
    )

    parser.add_argument(
        "--summary_file",
        default=Path(__file__).resolve().parent.parent.parent / "bazel_statistics.json",
        type=Path,
    )

    parser.add_argument(
        "--cachehit_csv",
    )

    parser.add_argument(
        "--distro",
        default="unknown",
    )
    return parser.parse_args()


def parse_execution_logs(log_files: list[Path]) -> Iterator[ExecutionMetrics]:
    """
    Parse the bazel execution logs.
    We need to use raw_decode as the logs are not a valid json, see:
    https://github.com/bazelbuild/bazel/issues/14209
    """
    for log_file in log_files:
        with open(log_file) as f:
            data = f.read()

        decoder = json.JSONDecoder()
        d = data
        while len(d):
            (parsed_data, offset) = decoder.raw_decode(d)
            d = d[offset:]
            yield ExecutionMetrics(**parsed_data)


def build_summary(parsed_logs: list[ExecutionMetrics]) -> Summary:
    overall_targets = len(parsed_logs)
    cache_hits = sum(1 for log in parsed_logs if log.cacheHit)

    return Summary(
        overallTargets=overall_targets,
        cacheHits=cache_hits,
        percentRemoteCacheHits=round(cache_hits / overall_targets * 100, 2),
        targetsWithMissedCache=[log.targetLabel for log in parsed_logs if not log.cacheHit],
        numberUncacheableTargets=sum(1 for log in parsed_logs if not log.cacheable),
        numberRemotableTargets=sum(1 for log in parsed_logs if log.remotable),
    )


def write_statistics(summary: Summary, file_name: Path) -> None:
    with open(file_name, "w") as f:
        json.dump(summary._asdict(), f)


def write_cachehit_csv(summary: Summary, file_path: Path, distro: str) -> None:
    print(f"Writing cachehit csv to {file_path}")
    with open(file_path, "w") as f:
        f.write(f'"{distro}"\n')
        f.write(f"{summary.percentRemoteCacheHits}\n")


def main():
    args = parse_arguments()

    bazel_log_files = list(args.execution_logs_root.glob(args.bazel_log_file_pattern))
    print("Analyzing the following log files: ")
    pp(bazel_log_files)

    summary = build_summary(list(parse_execution_logs(bazel_log_files)))
    write_statistics(summary, args.summary_file)
    pp(summary._asdict())

    if args.cachehit_csv:
        write_cachehit_csv(summary, args.cachehit_csv, args.distro)


if __name__ == "__main__":
    main()
