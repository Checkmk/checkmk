#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import argparse
from collections.abc import Sequence
from pathlib import Path

from cmk.ccc.version import __version__, Version
from cmk.werks.tool.config import RuntimeConfiguration
from cmk.werks.tool.models import EditionV2, EditionV3, WerkV3
from cmk.werks.tool.utils import (
    load_raw_files,
    resolve_version,
    write_precompiled_werks,
)
from cmk.werks.tool.utils.burn import main as burn
from cmk.werks.tool.utils.collect import main as collect


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
    return EditionV3(filter_by_edition)


def main_precompile(args: argparse.Namespace) -> None:
    werks_list = load_raw_files(args.werk_dir)

    rtc = RuntimeConfiguration(args.werk_dir.parent)

    filter_by_edition = _get_filter(args.filter_by_edition)

    current_version = Version.from_str(__version__)

    def _filter(werk: WerkV3) -> bool:
        edition = werk.edition

        # include only werks matching the edition filter (if any) and this major version
        return (filter_by_edition is None or edition == filter_by_edition) and (
            Version.from_str(resolve_version(rtc, werk.version)).base == current_version.base
        )

    werks = {werk.id: werk for werk in werks_list if _filter(werk)}

    write_precompiled_werks(args.destination, werks)


def main_collect(args: argparse.Namespace) -> None:
    branches = {}
    if args.substitute_branches:
        branches = dict(r.split(":", 1) for r in args.substitute_branches)
    collect(args.flavor, args.path, branches)


def main_burn(args: argparse.Namespace) -> None:
    burn(args.repo_root)


def parse_arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    subparsers.required = True

    parser_precompile = subparsers.add_parser(
        "precompile", help="Collect werk files of current major version into json."
    )
    parser_precompile.add_argument("werk_dir", type=path_dir, help=".werk folder in the git root")
    parser_precompile.add_argument("destination", type=Path)
    parser_precompile.add_argument(
        "--filter-by-edition",
        default=None,
        choices=[*(x.value for x in [*EditionV2, *EditionV3])],
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

    parser_burn = subparsers.add_parser(
        "burn", help="Burn released Checkmk version into Werks without version"
    )
    parser_burn.add_argument(
        "repo_root", type=path_dir, help="path to git repo, containing .werk folder"
    )
    parser_burn.set_defaults(func=main_burn)

    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_arguments(argv)
    args.func(args)


if __name__ == "__main__":
    main()
