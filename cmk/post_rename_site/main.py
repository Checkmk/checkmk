#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import logging
from itertools import chain
from typing import List

from livestatus import SiteId

import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.plugin_registry
import cmk.utils.site
from cmk.utils.log import VERBOSE
from cmk.utils.plugin_loader import load_plugins_with_exceptions
from cmk.utils.version import is_raw_edition

# This special script needs persistence and conversion code from different places of Checkmk. We may
# centralize the conversion and move the persistence to a specific layer in the future, but for the
# the moment we need to deal with it.
from cmk.gui import main_modules
from cmk.gui.logged_in import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context

from .registry import rename_action_registry

logger = logging.getLogger("cmk.post_rename_site")


def main(args: List[str]) -> int:
    arguments = parse_arguments(args)
    setup_logging(arguments)

    if arguments.debug:
        cmk.utils.debug.enable()
    logger.debug("parsed arguments: %s", arguments)

    new_site_id = SiteId(cmk.utils.site.omd_site())
    if arguments.old_site_id == new_site_id:
        logger.info("OLD_SITE_ID is equal to current OMD_SITE - Nothing to do.")
        return 0

    load_plugins()

    try:
        has_errors = run(arguments, arguments.old_site_id, new_site_id)
    except Exception:
        if arguments.debug:
            raise
        logger.exception(
            'ERROR: Please repair this and run "cmk-post-rename-site -v" '
            "BEFORE starting the site again."
        )
        return 1
    return 1 if has_errors else 0


def load_plugins() -> None:
    for plugin, exc in chain(
        load_plugins_with_exceptions("cmk.post_rename_site.plugins.actions"),
        load_plugins_with_exceptions("cmk.post_rename_site.cee.plugins.actions")
        if not is_raw_edition()
        else [],
    ):
        logger.error("Error in action plugin %s: %s\n", plugin, exc)
        if cmk.utils.debug.enabled():
            raise exc


def parse_arguments(args: List[str]) -> argparse.Namespace:
    def site_id(s: str) -> SiteId:
        if not s:
            raise ValueError("Must not be empty")
        return SiteId(s)

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "old_site_id",
        metavar="OLD_SITE_ID",
        type=site_id,
        help=("Specify the previous ID of the renamed site."),
    )
    p.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (use multiple times for more output)",
    )

    return p.parse_args(args)


def setup_logging(arguments: argparse.Namespace) -> None:
    log.setup_console_logging()
    log.logger.setLevel(log.verbosity_to_log_level(arguments.verbose))

    # TODO: Fix this cruel hack caused by our funny mix of GUI + console
    # stuff. Currently, we just move the console handler to the top, so
    # both worlds are happy. We really, really need to split business logic
    # from presentation code... :-/
    if log.logger.handlers:
        console_handler = log.logger.handlers[0]
        del log.logger.handlers[:]
        logging.getLogger().addHandler(console_handler)


def run(arguments: argparse.Namespace, old_site_id: SiteId, new_site_id: SiteId) -> bool:
    has_errors = False
    logger.debug("Initializing application...")

    main_modules.load_plugins()

    with gui_context(), SuperUserContext():
        logger.debug("Starting actions...")
        actions = sorted(rename_action_registry.values(), key=lambda a: a.sort_index)
        total = len(actions)
        for count, rename_action in enumerate(actions, start=1):
            logger.log(VERBOSE, " %i/%i %s...", count, total, rename_action.title)
            try:
                rename_action.run(old_site_id, new_site_id)
            except Exception:
                has_errors = True
                logger.error(' + "%s" failed', rename_action.title, exc_info=True)
                if arguments.debug:
                    raise

    logger.log(VERBOSE, "Done")
    return has_errors
