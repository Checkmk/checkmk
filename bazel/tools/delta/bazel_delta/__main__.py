# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The --delta option of the format, lint and mypy targets.

files  prints the branch the changes are compared to and then the changed
       files, each terminated by a NUL byte
"""

import os
import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from collections.abc import Sequence
from pathlib import Path

from bazel_delta.errors import DeltaError
from bazel_delta.files import delta_files, existing_files, find_base_branch, run_captured_in


def _parse_args(argv: Sequence[str]) -> Namespace:
    parser = ArgumentParser(
        prog="bazel run //bazel/tools/delta --",
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("files", help="print the base branch and the changed files")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    _parse_args(sys.argv[1:] if argv is None else argv)
    if not (workspace := os.environ.get("BUILD_WORKSPACE_DIRECTORY")):
        sys.exit("ERROR: run it with bazel run")
    run = run_captured_in(Path(workspace))
    try:
        base_branch = find_base_branch(run)
        files = existing_files(delta_files(run, base_branch))
    except DeltaError as e:
        sys.exit(f"ERROR: {e}")
    sys.stdout.write("".join(f"{entry}\0" for entry in [base_branch, *files]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
