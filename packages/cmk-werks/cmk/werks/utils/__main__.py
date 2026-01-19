#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import argparse
from pathlib import Path

from cmk.ccc.version import __version__, Version
from cmk.werks.models import EditionV2, EditionV3, WerkV2, WerkV3

from . import (
    edition_v2_to_v3,
    load_precompiled_werks_file,
    load_raw_files,
    write_as_text,
    write_precompiled_werks,
)
from .collect import main as collect


def path_dir(value: str) -> Path:
    result = Path(value)
    if not result.exists():
        raise argparse.ArgumentTypeError(f"File or directory does not exist: {result}")
    if not result.is_dir():
        raise argparse.ArgumentTypeError(f"{result} is not a directory")
    return result


def _get_filter(filter_by_edition: str | None) -> EditionV3 | None:
    if filter_by_edition is None:
        return None
    try:
        return edition_v2_to_v3(EditionV2(filter_by_edition))
    except ValueError:
        return EditionV3(filter_by_edition)


def main_precompile(args: argparse.Namespace) -> None:
    werks_list = load_raw_files(args.werk_dir)

    filter_by_edition = _get_filter(args.filter_by_edition)

    current_version = Version.from_str(__version__)

    def _filter(werk: WerkV2 | WerkV3) -> bool:
        if isinstance(werk.edition, EditionV2):
            edition = edition_v2_to_v3(werk.edition)
        else:
            edition = werk.edition

        if filter_by_edition is not None and edition != filter_by_edition:
            return False
        # only include werks of this major version:
        if Version.from_str(werk.version).base != current_version.base:
            return False
        return True

    werks = {werk.id: werk for werk in werks_list if _filter(werk)}

    write_precompiled_werks(args.destination, werks)


def main_changelog(args: argparse.Namespace) -> None:
    werks: dict[int, WerkV2 | WerkV3] = {}
    for path in (Path(p) for p in args.precompiled_werk):
        werks.update(load_precompiled_werks_file(path))

    with open(args.destination, "w", encoding="utf-8") as f:
        write_as_text(werks, f)


def main_collect(args: argparse.Namespace) -> None:
    branches = {}
    if args.substitute_branches:
        branches = dict(r.split(":", 1) for r in args.substitute_branches)
    collect(args.flavor, args.path, branches)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_changelog = subparsers.add_parser("changelog", help="Show who worked on a werk")
    parser_changelog.add_argument("destination")
    parser_changelog.add_argument("precompiled_werk", nargs="+")
    parser_changelog.set_defaults(func=main_changelog)

    parser_precompile = subparsers.add_parser(
        "precompile", help="Collect werk files of current major version into json."
    )
    parser_precompile.add_argument("werk_dir", type=path_dir, help=".werk folder in the git root")
    parser_precompile.add_argument("destination", type=Path)
    parser_precompile.add_argument(
        "--filter-by-edition",
        default=None,
        choices=[*map(lambda x: x.value, [*EditionV2, *EditionV3])],
    )
    parser_precompile.set_defaults(func=main_precompile)

    parser_collect = subparsers.add_parser(
        "collect", help="Collect werks from all branches, print json to stdout"
    )
    # if you want to compile the complete database of all werks, you have to go
    # through all branches and look at all .werks folders there.
    parser_collect.add_argument("flavor", choices=["cma", "cmk", "checkmk_kube_agent", "cloudmk"])
    parser_collect.add_argument("path", help="path to git repo to read werks from", type=path_dir)
    parser_collect.add_argument(
        "--substitute-branches",
        nargs="+",
        help="without this option the script autodetects branches with the prefix "
        "'refs/remotes/origin/'. During testing and developing, it might useful "
        "to disable the autodiscovery and explicitly set the branches. So you could "
        "use '2.3.0:HEAD' to only collect from HEAD and use 2.3.0 as branch name.",
    )
    parser_collect.set_defaults(func=main_collect)

    return parser.parse_args()


def main():
    args = parse_arguments()
    args.func(args)


if __name__ == "__main__":
    main()
