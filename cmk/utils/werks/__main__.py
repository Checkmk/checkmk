#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from collections.abc import Sequence
from pathlib import Path

from . import load_precompiled_werks_file, Werk, write_as_text


def main_changelog(args: argparse.Namespace) -> None:
    create_changelog(args.destination, [Path(p) for p in args.precompiled_werk])


def create_changelog(dest_file_path: str, precompiled_werk_files: Sequence[Path]) -> None:
    werks = load_werks(precompiled_werk_files)

    with open(dest_file_path, "w", encoding="utf-8") as f:
        write_as_text(werks, f)

        # TODO: ChangeLog.in was removed with
        # Change-Id: Ifa2b17349e4a4665fb3bc10d9b4c033ccdcf03a2
        # Append previous werk changes
        p = Path(dest_file_path + ".in")
        if p.exists():
            f.write("\n\n")
            f.write(p.read_text())


def load_werks(precompiled_werk_files: Sequence[Path]) -> dict[int, Werk]:
    werks: dict[int, Werk] = {}
    for path in precompiled_werk_files:
        werks.update(load_precompiled_werks_file(path))
    return werks


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_changelog = subparsers.add_parser("changelog", help="Show who worked on a werk")
    parser_changelog.add_argument("destination")
    parser_changelog.add_argument("precompiled_werk", nargs="+")
    parser_changelog.set_defaults(func=main_changelog)

    return parser.parse_args()


def main():
    args = parse_arguments()
    args.func(args)


if __name__ == "__main__":
    main()
