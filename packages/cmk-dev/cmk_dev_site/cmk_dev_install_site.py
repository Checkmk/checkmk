# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
from collections.abc import Iterator

from .cmk_dev_install import Edition, ExitCode  # type: ignore[attr-defined]
from .cmk_dev_install import run as cmk_dev_install
from .cmk_dev_site import main as cmk_dev_site
from .utils.cli import clean_cli_exit, report_duration
from .utils.log import get_logger
from .utils.update_check import check_for_update
from .version import __version__

logger = get_logger(__name__)


def setup_parser(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "version",
        metavar="build-version",
        nargs="?",
        default=None,
    )
    parser.add_argument(
        "edition",
        type=Edition,
        nargs="?",
        choices=Edition,
        default=None,
    )
    parser.add_argument(
        "-d",
        "--distributed",
        metavar="N",
        help="specify the number of distributed sites to set up.",
        type=int,
        default=0,
    )
    parser.add_argument(
        "-n",
        "--name",
        help="specify name of the site to be created",
    )
    parser.add_argument(
        "--dryrun",
        help="only print command, but do not execute",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="increase output verbosity",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="count",
        default=0,
        help="decrease output verbosity",
    )


def install_args(version: str | None, edition: str | None, arg_logging_level: str) -> Iterator[str]:
    if version:
        yield str(version)
        if edition:
            yield "--edition"
            yield str(edition)
    if arg_logging_level:
        yield arg_logging_level


def site_args(
    version: str | None,
    edition: str | None,
    distributed: int,
    arg_logging_level: str,
    name: str | None,
) -> Iterator[str]:
    if version:
        # cmk-dev-site takes the edition as a suffix on the version positional
        # (e.g. "3.0.0-2026-06-29.ultimate"), unlike cmk-dev-install's --edition.
        yield f"{version}.{edition}" if edition else str(version)
    if distributed:
        yield "--distributed"
        yield str(distributed)
    if name:
        yield "--name"
        yield name
    yield "-f"
    if arg_logging_level:
        yield arg_logging_level


def core(
    version: str | None,
    edition: str | None,
    *,
    site_distributed: int,
    site_name: str | None,
    dryrun: bool,
    verbose: int,
    quiet: int,
) -> int:
    # we build the commandline and then feed it to the original tools
    # so what we print and execute is exactly the same...
    arg_logging_level = ""
    if verbose or quiet:
        arg_logging_level = f"-{''.join(['v' * verbose, 'q' * quiet])}"

    args_install = list(install_args(version, edition, arg_logging_level))
    # preview with the user-supplied version; the real site step uses the
    # version resolved by cmk-dev-install (see below)
    args_site = list(site_args(version, edition, site_distributed, arg_logging_level, site_name))

    print(  # noqa: T201
        "cmk-dev-install",
        " ".join(args_install),
    )

    if dryrun:
        return 0

    install_result = cmk_dev_install(args_install)
    if install_result.exit_code != ExitCode.SUCCESS:
        return install_result.exit_code

    if install_result.installed_version:
        # cmk-dev-install resolved the version (e.g. "2.3" ->
        # "2.3.0-2026.07.10.cee", edition included). Forward it so
        # cmk-dev-site neither asks interactively for a partial version nor
        # falls back to the system default OMD version.
        args_site = list(
            site_args(
                install_result.installed_version,
                None,
                site_distributed,
                arg_logging_level,
                site_name,
            )
        )
        print("cmk-dev-site", " ".join(args_site))  # noqa: T201

    return cmk_dev_site(args_site)


def execute(args: argparse.Namespace) -> int:
    try:
        logger.setLevel(max(logging.INFO - ((args.verbose - args.quiet) * 10), logging.DEBUG))
        return core(
            args.version,
            args.edition,
            site_distributed=args.distributed,
            site_name=args.name,
            dryrun=args.dryrun,
            verbose=args.verbose,
            quiet=args.quiet,
        )
    except RuntimeError as e:
        logger.error(str(e))  # noqa: TRY400
        return 1
    return 0  # type: ignore[unreachable]


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(_sys_argv: list[str] | None = None) -> int:
    with check_for_update(), report_duration(), clean_cli_exit():
        parser = create_parser()
        setup_parser(parser)

        args = parser.parse_args()
        return execute(args)
