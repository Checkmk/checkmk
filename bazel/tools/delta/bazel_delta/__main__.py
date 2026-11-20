# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The --delta option of the format, lint and mypy targets.

files  prints the branch the changes are compared to and then the changed
       files, each terminated by a NUL byte
lint   lints the targets of the changed files, run by //:lint and //:lint.check
"""

import os
import sys
from argparse import ArgumentParser, Namespace, RawDescriptionHelpFormatter
from collections.abc import Sequence
from pathlib import Path

from bazel_delta.errors import DeltaError
from bazel_delta.files import delta_files, existing_files, find_base_branch, run_captured_in
from bazel_delta.lint import Buildifier, lint_delta, workspace_in


def _parse_args(argv: Sequence[str]) -> Namespace:
    parser = ArgumentParser(
        prog="bazel run //bazel/tools/delta --",
        description=__doc__,
        formatter_class=RawDescriptionHelpFormatter,
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("files", help="print the base branch and the changed files")
    # Without abbreviations, as Bazel flags such as --build would match --buildifier
    lint = subcommands.add_parser(
        "lint", help="lint the targets of the changed files", allow_abbrev=False
    )
    lint.add_argument("--fix", action="store_true", help="fix what the linters can")
    lint.add_argument("--buildifier", type=Path, required=True, help="buildifier binary")
    lint.add_argument("--buildifier_config", type=Path, required=True, help=".buildifier.json")
    lint.add_argument(
        "--starlark_exclude",
        action="append",
        default=[],
        help="path pattern buildifier skips",
    )
    lint.add_argument(
        "--starlark_name",
        action="append",
        default=[],
        help="name pattern buildifier takes",
    )
    lint.add_argument("--delta", action="store_true", help="lint the targets of the changed files")
    # The other options are Bazel flags for the nested `bazel lint`, as those
    # given to `bazel run` don't reach it
    args, bazel_flags = parser.parse_known_args(argv)
    if bazel_flags and args.command == "files":
        parser.error(f"unrecognized arguments: {' '.join(bazel_flags)}")
    args.bazel_flags = bazel_flags
    return args


def _files(workspace: Path) -> int:
    run = run_captured_in(workspace)
    base_branch = find_base_branch(run)
    files = existing_files(delta_files(run, base_branch))
    sys.stdout.write("".join(f"{entry}\0" for entry in [base_branch, *files]))
    return 0


def _lint(workspace: Path, args: Namespace) -> int:
    if not args.delta:
        target = "//:lint" if args.fix else "//:lint.check"
        sys.exit(
            "ERROR: only --delta is supported.\n"
            f"Use 'bazel run {target} -- --delta', or 'bazel lint <targets>' to lint specific targets."
        )
    # Relative to the runfiles directory, the working directory of `bazel run`
    buildifier = Buildifier(
        args.buildifier.absolute(),
        args.buildifier_config.absolute(),
        args.starlark_exclude,
        args.starlark_name,
    )
    return lint_delta(workspace_in(workspace), buildifier, args.fix, args.bazel_flags)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    if not (workspace := os.environ.get("BUILD_WORKSPACE_DIRECTORY")):
        sys.exit("ERROR: run it with bazel run")
    try:
        return _lint(Path(workspace), args) if args.command == "lint" else _files(Path(workspace))
    except DeltaError as e:
        sys.exit(f"ERROR: {e}")


if __name__ == "__main__":
    sys.exit(main())
