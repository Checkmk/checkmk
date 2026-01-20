#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
from pathlib import Path

from cmk.utils.version import __version__, Version

from cmk.werks.models import Edition, Werk, WerkV3

from . import (
    load_precompiled_werks_file,
    load_raw_files,
    write_as_text,
    write_precompiled_werks,
)
from .announce import main as main_announce
from .collect import main as collect
from .mail import main as mail


def main_changelog(args: argparse.Namespace) -> None:
    werks: dict[int, Werk] = {}
    for path in (Path(p) for p in args.precompiled_werk):
        werks.update(load_precompiled_werks_file(path))

    with open(args.destination, "w", encoding="utf-8") as f:
        write_as_text(werks, f)


def main_precompile(args: argparse.Namespace) -> None:
    werks_list = load_raw_files(args.werk_dir)

    filter_by_edition = (
        Edition(args.filter_by_edition) if args.filter_by_edition is not None else None
    )
    current_version = Version.from_str(__version__)

    def _filter(werk: Werk | WerkV3) -> bool:
        if filter_by_edition is not None and werk.edition != filter_by_edition:
            return False
        # only include werks of this major version:
        if Version.from_str(werk.version).base != current_version.base:
            return False
        return True

    werks = {werk.id: werk for werk in werks_list if _filter(werk)}

    write_precompiled_werks(args.destination, werks)


def main_collect(args: argparse.Namespace) -> None:
    branches = {}
    if args.substitute_branches:
        branches = dict(r.split(":", 1) for r in args.substitute_branches)
    collect(args.flavor, args.path, branches)


def main_mail(args: argparse.Namespace) -> None:
    mail(args)


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

    parser_precompile = subparsers.add_parser(
        "precompile", help="Collect werk files of current major version into json."
    )
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
    parser_announce.set_defaults(func=main_announce)

    parser_collect = subparsers.add_parser(
        "collect", help="Collect werks from all branches, print json to stdout"
    )
    # if you want to compile the complete database of all werks, you have to go
    # through all branches and look at all .werks folders there.
    parser_collect.add_argument("flavor", choices=["cma", "cmk", "checkmk_kube_agent"])
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

    parser_mail = subparsers.add_parser(
        "mail",
        help="Step through git commits and send out one mail for each werk change. "
        "Commit is annotated by 'git notes' when a mail is sent.",
    )
    parser_mail.add_argument(
        "repo_path",
        help="path to git repo to read changes from",
        type=path_dir,
    )
    parser_mail.add_argument(
        "branch",
        help="which branch to check for new werks, should look like refs/remotes/origin/<branch_name>",
    )
    parser_mail.add_argument(
        "ref",
        help="reference for git notes, should be werk_mail for production.",
    )
    parser_mail.add_argument(
        "--ref-fixup",
        default="werk_mail_fixup",
        help="reference for git notes for fixing broken werk commits",
    )
    parser_mail.add_argument(
        "--do-fetch-git-notes",
        help="fetch git notes before interacting with them",
        action="store_true",
    )
    parser_mail.add_argument(
        "--do-push-git-notes",
        help="push git notes after interacting with them",
        action="store_true",
    )
    parser_mail.add_argument(
        "--do-send-mail",
        help="actually send mails, otherwise just print them.",
        action="store_true",
    )
    parser_mail.add_argument(
        "--do-add-notes",
        help="actually add notes, otherwise just print them.",
        action="store_true",
    )
    parser_mail.add_argument(
        "--mail",
        help="do not send mails to the official mailing lists, but the mail specified here",
    )
    parser_mail.add_argument(
        "--assume-no-notes-but",
        help="do not look up notes with git command, but assume a single note at GIT-HASH.",
        metavar="GIT-HASH",
    )
    parser_mail.set_defaults(func=main_mail)

    return parser.parse_args()


def main():
    args = parse_arguments()
    args.func(args)


if __name__ == "__main__":
    main()
