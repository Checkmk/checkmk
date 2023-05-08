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
from .werk import Edition


def main_changelog(args: argparse.Namespace) -> None:
    werks: dict[int, Werk] = {}
    for path in (Path(p) for p in args.precompiled_werk):
        werks.update(load_precompiled_werks_file(path))

    with open(args.destination, "w", encoding="utf-8") as f:
        write_as_text(werks, f)


def main_precompile(args: argparse.Namespace) -> None:
    if not args.werk_dir.exists():
        raise Exception("Requested werk directory does not exist: %s" % args.werk_dir)

    werks_list = load_raw_files(args.werk_dir)

    werks = {
        werk.id: werk
        for werk in werks_list
        if args.filter_by_edition is None
        # we don't know if we have a WerkV1 or WerkV2, so we test for both:
        or werk.edition == args.filter_by_edition or werk.edition == Edition(args.filter_by_edition)
    }

    write_precompiled_werks(args.destination, werks)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_changelog = subparsers.add_parser("changelog", help="Show who worked on a werk")
    parser_changelog.add_argument("destination")
    parser_changelog.add_argument("precompiled_werk", nargs="+")
    parser_changelog.set_defaults(func=main_changelog)

    parser_precompile = subparsers.add_parser("precompile", help="Collect werk files into json.")
    parser_precompile.add_argument("werk_dir", type=Path, help=".werk in the git root")
    parser_precompile.add_argument("destination", type=Path)
    parser_precompile.add_argument(
        "--filter-by-edition", default=None, help="cee, cre, cce or others"
    )
    parser_precompile.set_defaults(func=main_precompile)

    return parser.parse_args()


def main():
    args = parse_arguments()
    args.func(args)


if __name__ == "__main__":
    main()
