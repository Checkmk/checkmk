#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import sys
from pathlib import Path

from sarif import __version__ as SARIF_TOOLS_PACKAGE_VERSION  # type: ignore[import-untyped]
from sarif.operations import copy_op  # type: ignore[import-untyped]
from sarif.sarif_file import SarifFile, SarifFileSet  # type: ignore[import-untyped]

SARIF_MIN_SIZE = 0


def load_all(root_dir: Path) -> SarifFileSet:
    results = SarifFileSet()
    for file_path in root_dir.rglob("*AspectRulesLint*.report"):
        try:
            if file_path.stat().st_size <= SARIF_MIN_SIZE:
                continue

            with file_path.open("rt") as fd:
                results.add_file(SarifFile(file_path, json.load(fd)))
        except (json.JSONDecodeError, OSError) as exc:
            sys.stderr.write(f"{file_path!s}: {exc!s}\n")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_dir", type=Path, default="bazel-bin")
    parser.add_argument("--output", type=Path, default="out.sarif")
    args = parser.parse_args(sys.argv[1:])
    results = load_all(args.root_dir)
    copy_op.generate_sarif(
        input_files=results,
        output=args.output,
        append_timestamp=False,
        sarif_tools_version=SARIF_TOOLS_PACKAGE_VERSION,
        cmdline="bazel lint",
    )


if __name__ == "__main__":
    main()
