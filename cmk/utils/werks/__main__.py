#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from pathlib import Path

from . import (
    load_precompiled_werks_file,
    load_raw_files,
    Werk,
    write_as_text,
    write_precompiled_werks,
)
from .announce import main as main_announce
from .werk import Edition


def main_changelog(args: argparse.Namespace) -> None:
    werks: dict[int, Werk] = {}
    for path in (Path(p) for p in args.precompiled_werk):
        werks.update(load_precompiled_werks_file(path))

    with open(args.destination, "w", encoding="utf-8") as f:
        write_as_text(werks, f)


def main_precompile(args: argparse.Namespace) -> None:
    werks_list = load_raw_files(args.werk_dir)

    werks = {
        werk.id: werk
        for werk in werks_list
        if args.filter_by_edition is None
        # TODO: Use werk.to_werk().edition == Edition(args.filter_by_edition)
        or werk.edition == args.filter_by_edition or werk.edition == Edition(args.filter_by_edition)
    }

    write_precompiled_werks(args.destination, werks)


def path_dir(value: str) -> Path:
    result = Path(value)
    if not result.exists():
        raise argparse.ArgumentTypeError(f"File or directory does not exist: {result}")
    if not result.is_dir():
        raise argparse.ArgumentTypeError(f"{result} is not a directory")
    return result


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_changelog = subparsers.add_parser("changelog", help="Show who worked on a werk")
    parser_changelog.add_argument("destination")
    parser_changelog.add_argument("precompiled_werk", nargs="+")
    parser_changelog.set_defaults(func=main_changelog)

    parser_precompile = subparsers.add_parser("precompile", help="Collect werk files into json.")
    parser_precompile.add_argument("werk_dir", type=path_dir, help=".werk folder in the git root")
    parser_precompile.add_argument("destination", type=Path)
    parser_precompile.add_argument(
        "--filter-by-edition",
        default=None,
        choices=list(x.value for x in Edition),
    )
    parser_precompile.set_defaults(func=main_precompile)

    parser_announce = subparsers.add_parser("announce", help="Output announce text")
    parser_announce.add_argument("werk_dir", type=path_dir, help=".werk folder in the git root")
    parser_announce.add_argument("version")
    parser_announce.add_argument("--format", choices=("txt", "md"), default="txt")
    parser_announce.add_argument("--feedback-mail", default="feedback@checkmk.com")
    parser_announce.set_defaults(func=main_announce)

    return parser.parse_args()


def main():
    args = parse_arguments()
    args.func(args)


if __name__ == "__main__":
    main()
