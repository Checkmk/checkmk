#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tool for updating Checkmk configuration files after version updates

This command is normally executed automatically at the end of "omd update" on
all sites and on remote sites after receiving a snapshot and does not need to
be called manually.
"""

import argparse
import logging
from collections.abc import Sequence
from itertools import chain
from pathlib import Path
from typing import Final

from cmk.utils import debug, log, paths, tty
from cmk.utils.log import VERBOSE
from cmk.utils.plugin_loader import load_plugins_with_exceptions
from cmk.utils.version import is_raw_edition

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
from cmk.base import config as base_config
from cmk.base.check_api import get_check_api_context

from cmk.gui import main_modules
from cmk.gui.log import logger as gui_logger
from cmk.gui.logged_in import SuperUserContext
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.changes import ActivateChangesWriter, add_change
from cmk.gui.watolib.hosts_and_folders import disable_redis

from .registry import update_action_registry
from .update_state import UpdateState


def main(args: Sequence[str]) -> bool:
    arguments = _parse_arguments(args)
    logger = _setup_logging(arguments)

    if arguments.debug:
        debug.enable()

    update_state = UpdateState.load(Path(paths.var_dir))
    _load_plugins(logger)

    try:
        return ConfigUpdater(logger, update_state)()
    except Exception:
        if debug.enabled():
            raise
        logger.exception(
            'ERROR: Please repair this and run "cmk-update-config -v" '
            "BEFORE starting the site again."
        )
        return False


def _parse_arguments(args: Sequence[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    p.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Verbose mode (use multiple times for more output)",
    )
    return p.parse_args(args)


def _setup_logging(arguments: argparse.Namespace) -> logging.Logger:
    level = log.verbosity_to_log_level(arguments.verbose)

    log.setup_console_logging()
    log.logger.setLevel(level)

    logger = logging.getLogger("cmk.update_config")
    logger.setLevel(level)
    logger.debug("parsed arguments: %s", arguments)

    # TODO: Fix this cruel hack caused by our funny mix of GUI + console
    # stuff. Currently, we just move the console handler to the top, so
    # both worlds are happy. We really, really need to split business logic
    # from presentation code... :-/
    if log.logger.handlers:
        console_handler = log.logger.handlers[0]
        del log.logger.handlers[:]
        logging.getLogger().addHandler(console_handler)

    gui_logger.setLevel(_our_logging_level_to_gui_logging_level(logger.getEffectiveLevel()))

    return logger


def _our_logging_level_to_gui_logging_level(lvl: int) -> int:
    """The default in cmk.gui is WARNING, whereas our default is INFO. Hence, our default
    corresponds to INFO in cmk.gui, which results in too much logging.
    """
    return lvl + 10


def _load_plugins(logger: logging.Logger) -> None:
    for plugin, exc in chain(
        load_plugins_with_exceptions("cmk.update_config.plugins.actions"),
        load_plugins_with_exceptions("cmk.update_config.cee.plugins.actions")
        if not is_raw_edition()
        else [],
    ):
        logger.error("Error in action plugin %s: %s\n", plugin, exc)
        if debug.enabled():
            raise exc


class ConfigUpdater:
    def __init__(self, logger: logging.Logger, update_state: UpdateState) -> None:
        self._logger: Final = logger
        self.update_state: Final = update_state

    def __call__(self) -> bool:
        self._has_errors = False
        self._logger.log(VERBOSE, "Initializing application...")

        main_modules.load_plugins()

        actions = sorted(update_action_registry.values(), key=lambda a: a.sort_index)
        total = len(actions)

        # Note: Redis has to be disabled first, the other contexts depend on it
        with disable_redis(), gui_context(), SuperUserContext():
            self._check_failed_gui_plugins()
            self._initialize_base_environment()

            self._logger.log(VERBOSE, "Updating Checkmk configuration...")
            self._logger.log(
                VERBOSE,
                f"{tty.red}ATTENTION: Some steps may take a long time depending "
                f"on your installation, e.g. during major upgrades.{tty.normal}",
            )

            for count, action in enumerate(actions, start=1):
                self._logger.log(VERBOSE, " %i/%i %s..." % (count, total, action.title))
                try:
                    with ActivateChangesWriter.disable():
                        action(self._logger, self.update_state.setdefault(action.name))
                except Exception:
                    self._has_errors = True
                    self._logger.error(' + "%s" failed' % action.title, exc_info=True)
                    if debug.enabled():
                        raise

            if not self._has_errors and not is_wato_slave_site():
                # Force synchronization of the config after a successful configuration update
                add_change(
                    "cmk-update-config",
                    "Successfully updated Checkmk configuration",
                    need_sync=True,
                )

        self.update_state.save()
        self._logger.log(VERBOSE, "Done")
        return self._has_errors

    def _check_failed_gui_plugins(self) -> None:
        if get_failed_plugins():
            self._logger.error("")
            self._logger.error(
                "ERROR: Failed to load some GUI plugins. You will either have \n"
                "       to remove or update them to be compatible with this \n"
                "       Checkmk version."
            )
            self._logger.error("")

    def _initialize_base_environment(self) -> None:
        # Failing to load the config here will result in the loss of *all* services due to (...)
        # EDIT: This is no longer the case; but we probably need the config for other reasons?
        base_config.load()
        base_config.load_all_agent_based_plugins(get_check_api_context)
