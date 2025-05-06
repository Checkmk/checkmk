#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This script helps managing Bandit '# nosec' exclusions in our codebase.
It can scan the codebase for all instances of '# nosec' and cross-reference
them with our document to track their reasoning (i.e. 'bandit-exclusions.md').
It also helps throwing the dice for new Bandit nosec IDs to use in said doc.

Call with --help for usage.
"""

from __future__ import annotations

import argparse
import logging
import random
import re
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TypeVar

DEFAULT_DOC = Path("bandit-exclusions.md")
ID_LEN = 6
BNS_PATTERN = rf"BNS:[0-9a-f]{{{ID_LEN}}}"
NOSEC_PATTERN = "# nosec"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="""Manage and annotate Bandit nosec IDs (BNS IDs).
        To check the codebase for unannotated '# nosec' markers, use `check`.
        To obtain a new BNS ID to annotate a '# nosec' marker, use `new`.
        """
    )
    parser.add_argument(
        "-d",
        "--doc",
        default=DEFAULT_DOC,
        type=Path,
        help=f"The target exclusions document (default: {DEFAULT_DOC})",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="available commands",
        description=f"run `{parser.prog} <command> --help` for detailed usage",
        required=True,
    )

    # -- new --

    parser_new = subparsers.add_parser("new", help="Get a new Bandit nosec ID")
    parser_new.set_defaults(run=cmd_new)

    # -- check --

    parser_check = subparsers.add_parser(
        "check",
        help="Check the codebase for nosec markers and make sure they are annotated",
    )
    parser_check.add_argument(
        "src_root", help="Path to the Check_MK repository root directory", type=Path
    )
    parser_check.add_argument(
        "-v",
        "--verbose",
        help="Show the more context for unannotated nosec markers",
        action="store_true",
    )
    parser_check.add_argument(
        "-x",
        "--exclude",
        default="tests",
        help="Comma separated list of paths to exclude, relative to 'src_root' (default: 'tests')",
        type=str,
        action="store",
    )
    parser_check.add_argument(
        "--rg",
        help="use ripgrep to find '# nosec' markers; much faster, less accurate (experimental, not for CI, '-x' is ignored)",
        action="store_true",
    )
    parser_check.set_defaults(run=cmd_check)

    # -- local-check --

    parser_local_check = subparsers.add_parser(
        "local-check",
        help="Output results as Checkmk local check output",
    )

    parser_local_check.add_argument(
        "-x",
        "--exclude",
        default="tests",
        help="Comma separated list of paths to exclude, relative to 'src_root' (default: 'tests')",
        type=str,
        action="store",
    )
    parser_local_check.add_argument(
        "src_root", help="Path to the Check_MK repository root directory", type=Path
    )
    parser_local_check.set_defaults(run=cmd_local_check)

    # -- find --

    parser_find = subparsers.add_parser(
        "find",
        help="Find all occurrences of a BNS ID in the code base",
    )
    parser_find.add_argument(
        "src_root", help="Path to the Check_MK repository root directory", type=Path
    )
    parser_find.add_argument("bns_id", help="The BNS ID to look for", type=BnsId)
    parser_find.set_defaults(run=cmd_find)

    return parser.parse_args()


T = TypeVar("T")


def _partition(
    predicate: Callable[[T], bool], input_list: Sequence[T]
) -> tuple[Sequence[T], Sequence[T]]:
    yes, no = [], []
    for i in input_list:
        if predicate(i):
            yes.append(i)
        else:
            no.append(i)
    return yes, no


class BnsId:
    @classmethod
    def generate(cls, excluded_ids: Sequence[BnsId]) -> BnsId:
        """Generate a BNS ID, making sure it's not present in excluded_ids"""
        while (new_id := cls._random_id()) in excluded_ids:
            pass  # unlikely, but try again
        return new_id

    def __init__(self, id_: str):
        if not re.match(rf"^{BNS_PATTERN}$", id_):
            raise ValueError("Invalid BNS ID")
        self._id = id_

    def __repr__(self) -> str:
        return self._id

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BnsId):
            return NotImplemented
        return self._id == other._id

    @staticmethod
    def _random_id() -> BnsId:
        return BnsId(f"BNS:{hex(random.randint(0, int('F' * ID_LEN, 16)))[2:].rjust(6, '0')}")


def existing_ids(exclusions_doc: Path) -> Sequence[BnsId]:
    """All existing IDs in the document as raw strings"""
    with open(exclusions_doc, encoding="utf-8") as f:
        return list(map(BnsId, re.findall(BNS_PATTERN, f.read())))


def add_entry(bns_id: BnsId, exclusions_doc: Path) -> None:
    """Add an ID to the document"""
    with open(exclusions_doc, "r+", encoding="utf-8") as f:
        # VERY basic sanity check
        if not f.readlines()[-1].startswith("|"):
            sys.exit(
                f"Failed to find table of BNS IDs in {exclusions_doc}. "
                "Make sure the table is at the very bottom of the document."
            )
        f.write(f"| `{bns_id}` | `BXXX` | Please add a description. |\n")


class Nosec:
    """A nosec marker in the codebase"""

    file: Path
    line_no: int
    line: str
    bns_id: BnsId | None

    def __init__(self, path: Path, line_no: int, raw_line: str):
        self.file = path
        self.line_no = line_no
        self.line = raw_line
        bns_match = re.search(BNS_PATTERN, raw_line)
        self.bns_id = None if bns_match is None else BnsId(bns_match[0])

    @property
    def location(self) -> str:
        """Report the file and line number of this marker"""
        return f"{self.file}:{self.line_no}"

    def __repr__(self) -> str:
        return f"{self.location}\n>\t{self.line}"


def find_nosecs(src_root: Path, excluded: Sequence[Path]) -> Sequence[Nosec]:
    """Scan the codebase for '# nosec' markers"""

    if not (src_root / "scripts").is_dir():
        # we need the find-python-files script and this is an easy sanity check
        sys.exit(
            f"Failed to find folder 'scripts' in '{src_root}'. Is this really the check_mk repo?"
        )

    def _format_output(output: bytes) -> Sequence[str]:
        return output.strip().decode("utf-8").split("\n")

    run_find_files = "./scripts/find-python-files"
    files = _format_output(
        subprocess.run(run_find_files, cwd=src_root, check=False, capture_output=True).stdout
    )
    logging.info(
        f"Checking {len(files)} python files in '{src_root}'"
        + (f" excluding '{', '.join(map(str, excluded))}'." if excluded else "")
    )

    result = []
    for f in files:
        if any(f.startswith(str(p)) for p in excluded):
            continue
        matches = subprocess.run(
            ["grep", "-n", NOSEC_PATTERN, f],
            check=False,  # grep will fail for files w/o nosec
            capture_output=True,
        )
        if matches.returncode != 0:
            continue
        for line in _format_output(matches.stdout):
            l_num, l_txt = line.split(":", maxsplit=1)
            result.append(Nosec(Path(f), int(l_num), l_txt))

    return result


def find_nosecs_rg(src_root: Path) -> Sequence[Nosec]:
    """Scan the codebase for '# nosec' markers using ripgrep (rg)"""
    matches = subprocess.run(
        ["rg", "--color", "never", "--line-number", NOSEC_PATTERN, str(src_root)],
        check=False,
        capture_output=True,
    )

    if matches.returncode != 0:
        return []

    result = []
    for line in matches.stdout.strip().decode("utf-8").split(str(src_root) + "/")[1:]:
        filename, l_num, l_txt = line.split(":", maxsplit=2)
        result.append(Nosec(src_root / filename, int(l_num), l_txt))
    return result


def cmd_new(args: argparse.Namespace) -> None:
    existing = existing_ids(args.doc)
    new_id = BnsId.generate(existing)
    add_entry(new_id, args.doc)
    print(
        f"Please use the ID '{new_id}'. "
        f"I've prepared a new entry in '{args.doc}' for your description.\n"
        "Mark the exclusion in the source code as follows:\n"
        f"# nosec <rule id> # {new_id}"
    )


def cmd_check(args: argparse.Namespace) -> None:
    fail = False

    logging.getLogger().setLevel(logging.INFO)

    excluded_paths = (
        []  # exclude nothing (as opposed to src_root/"")
        if args.exclude == ""
        else [args.src_root.resolve() / e for e in args.exclude.split(",")]
    )

    if args.rg:
        markers = find_nosecs_rg(args.src_root)
    else:
        markers = find_nosecs(args.src_root, excluded_paths)

    print(f"Found {len(markers)} '# nosec' markers.")

    annotated, not_annotated = _partition(lambda marker: marker.bns_id is not None, markers)

    def _show_markers(markers: Sequence[Nosec]) -> None:
        for marker in markers:
            print(marker if args.verbose else marker.location)

    if (count := len(not_annotated)) > 0:
        fail = True
        print(
            f"{count} markers are not annotated with a BNS ID. "
            "Please add annotations for the following occurrences:"
        )
        _show_markers(not_annotated)

    bns_ids = existing_ids(args.doc)
    invalid = [m for m in annotated if m.bns_id not in bns_ids]
    if (count := len(invalid)) > 0:
        fail = True
        print(f"{count} markers have a BNS ID that is not present in {args.doc}:")
        _show_markers(invalid)

    if fail:
        sys.exit(1)


def cmd_local_check(args: argparse.Namespace) -> None:
    excluded_paths = (
        [] if args.exclude == "" else [args.src_root.resolve() / e for e in args.exclude.split(",")]
    )
    markers = find_nosecs(args.src_root, excluded_paths)
    annotated, not_annotated = _partition(lambda marker: marker.bns_id is not None, markers)
    bns_ids = existing_ids(args.doc)
    invalid = [m for m in annotated if m.bns_id not in bns_ids]

    sum_not_annotated = len(not_annotated)
    sum_annotated = len(annotated)
    sum_invalid = len(invalid)
    sum_valid = sum_annotated - sum_invalid
    print(
        " ".join(
            (
                "P",
                '"[SecDev] Bandit markers"',
                "|".join(
                    (
                        f"not_annotated={sum_not_annotated};1;5",
                        f"invalid={sum_invalid};1;5",
                        f"valid={sum_valid}",
                    )
                ),
                f"Found {sum_annotated} annotations of which {sum_invalid} were invalid and {sum_not_annotated} unnotated nosecs",
            )
        )
    )


def cmd_find(args: argparse.Namespace) -> None:
    markers = find_nosecs(args.src_root, [])
    annotated, _ = _partition(lambda marker: marker.bns_id is not None, markers)

    found = list(filter(lambda m: m.bns_id == args.bns_id, annotated))
    print(f"BNS ID {args.bns_id} found {len(found)} time(s):")
    for marker in found:
        print(marker)


if __name__ == "__main__":
    args = parse_args()
    args.run(args)
