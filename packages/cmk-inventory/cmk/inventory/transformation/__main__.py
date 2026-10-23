#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
import os
import subprocess
import sys
from argparse import ArgumentParser, Namespace
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from .tree_files import show_transformation_results, transform_inventory_trees

logger = logging.getLogger(__name__)


def _parse_arguments(argv: Sequence[str]) -> Namespace:
    parser = ArgumentParser(prog="cmk-transform-inventory-trees")
    parser.add_argument(
        "--debug",
        action="store_true",
        default=False,
        help="Catch Python exceptions",
    )
    parser.add_argument(
        "--show-results",
        action="store_true",
        default=False,
        help="Show results",
    )
    parser.add_argument(
        "--bundle-length",
        type=int,
        default=0,
        help="Specify the bundle length. Only applies if no host names are given.",
    )
    parser.add_argument(
        "--host-name",
        nargs="*",
        default=[],
        help="Transform inventory trees of host names",
    )
    return parser.parse_args(args=argv[1:])


def _collect_hosts(logger: logging.Logger) -> Sequence[str]:
    try:
        return list(
            set(
                subprocess.check_output(
                    ["check_mk", "--list-hosts", "--all-sites", "--include-offline"],
                    encoding="utf-8",
                ).splitlines()
            )
        )
    except subprocess.CalledProcessError:
        logger.exception("Failed to collect all host names")
        return []


class HostNamesCollector(Protocol):
    def __call__(self, logger: logging.Logger, /) -> Sequence[str]: ...


def run(
    argv: Sequence[str],
    *,
    omd_root: Path,
    logger: logging.Logger,
    collect_host_names: HostNamesCollector = _collect_hosts,
) -> int:
    args = _parse_arguments(argv)
    try:
        if args.show_results:
            return show_transformation_results(
                omd_root=omd_root,
                filter_host_names=args.host_name,
                all_host_names=collect_host_names(logger),
            )
        return transform_inventory_trees(
            logger=logger,
            omd_root=omd_root,
            bundle_length=args.bundle_length,
            filter_host_names=args.host_name,
            all_host_names=collect_host_names(logger),
        )
    except Exception:
        logger.exception("Failed to transform inventory trees")
        return 1


def main() -> int:
    return run(sys.argv, omd_root=Path(os.environ.get("OMD_ROOT", "")), logger=logger)


if __name__ == "__main__":
    sys.exit(main())
