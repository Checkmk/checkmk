#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse

from livestatus import SiteId

import cmk.utils.debug
import cmk.utils.plugin_registry
import cmk.utils.site
from cmk.utils.log import VERBOSE
from cmk.utils.plugin_loader import load_plugins_with_exceptions, PluginFailures
from cmk.utils.version import is_cloud_edition, is_raw_edition

# This special script needs persistence and conversion code from different places of Checkmk. We may
# centralize the conversion and move the persistence to a specific layer in the future, but for the
# the moment we need to deal with it.
from cmk.gui import main_modules
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context

from .logger import logger, setup_logging
from .registry import rename_action_registry


def main(args: list[str]) -> int:
    arguments = parse_arguments(args)
    setup_logging(verbose=arguments.verbose)

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
    for plugin, exc in _load_plugins():
        logger.error("Error in action plugin %s: %s\n", plugin, exc)
        if cmk.utils.debug.enabled():
            raise exc


def _load_plugins() -> PluginFailures:
    yield from load_plugins_with_exceptions("cmk.post_rename_site.plugins.actions")
    if not is_raw_edition():
        yield from load_plugins_with_exceptions("cmk.post_rename_site.cee.plugins.actions")
    if is_cloud_edition():
        yield from load_plugins_with_exceptions("cmk.post_rename_site.cce.plugins.actions")


def parse_arguments(args: list[str]) -> argparse.Namespace:
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
