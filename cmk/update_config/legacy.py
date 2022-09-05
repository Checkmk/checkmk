#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tool for updating Checkmk configuration files after version updates

This command is normally executed automatically at the end of "omd update" on
all sites and on remote sites after receiving a snapshot and does not need to
be called manually.
"""
import argparse
import logging
import re
from datetime import datetime
from typing import Callable, List, Tuple

import cmk.utils
import cmk.utils.debug
import cmk.utils.log as log
import cmk.utils.paths
import cmk.utils.site
import cmk.utils.tty as tty
from cmk.utils.log import VERBOSE
from cmk.utils.type_defs import UserId

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
import cmk.base.autochecks
import cmk.base.check_api
import cmk.base.config

import cmk.gui.config
import cmk.gui.groups
import cmk.gui.utils
import cmk.gui.watolib.groups
import cmk.gui.watolib.hosts_and_folders
import cmk.gui.watolib.rulesets
import cmk.gui.watolib.tags
from cmk.gui import main_modules
from cmk.gui.log import logger as gui_logger
from cmk.gui.logged_in import SuperUserContext
from cmk.gui.plugins.userdb.utils import USER_SCHEME_SERIAL
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.userdb import load_users, save_users, Users
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.changes import ActivateChangesWriter, add_change


class UpdateConfig:
    def __init__(self, logger: logging.Logger, arguments: argparse.Namespace) -> None:
        super().__init__()
        self._arguments = arguments
        self._logger = logger
        # TODO: Fix this cruel hack caused by our funny mix of GUI + console
        # stuff. Currently, we just move the console handler to the top, so
        # both worlds are happy. We really, really need to split business logic
        # from presentation code... :-/
        if log.logger.handlers:
            console_handler = log.logger.handlers[0]
            del log.logger.handlers[:]
            logging.getLogger().addHandler(console_handler)
        self._has_errors = False
        gui_logger.setLevel(
            _our_logging_level_to_gui_logging_level(self._logger.getEffectiveLevel())
        )

    def run(self) -> bool:
        self._has_errors = False
        self._logger.log(VERBOSE, "Initializing application...")

        main_modules.load_plugins()

        # Note: Redis has to be disabled first, the other contexts depend on it
        with cmk.gui.watolib.hosts_and_folders.disable_redis(), gui_context(), SuperUserContext():
            self._check_failed_gui_plugins()
            self._initialize_base_environment()

            self._logger.log(VERBOSE, "Updating Checkmk configuration...")
            self._logger.log(
                VERBOSE,
                f"{tty.red}ATTENTION: Some steps may take a long time depending "
                f"on your installation, e.g. during major upgrades.{tty.normal}",
            )
            total = len(self._steps())
            for count, (step_func, title) in enumerate(self._steps(), start=1):
                self._logger.log(VERBOSE, " %i/%i %s..." % (count, total, title))
                try:
                    with ActivateChangesWriter.disable():
                        step_func()
                except Exception:
                    self._has_errors = True
                    self._logger.error(' + "%s" failed' % title, exc_info=True)
                    if self._arguments.debug:
                        raise

            if not self._has_errors and not is_wato_slave_site():
                # Force synchronization of the config after a successful configuration update
                add_change(
                    "cmk-update-config",
                    "Successfully updated Checkmk configuration",
                    need_sync=True,
                )

        self._logger.log(VERBOSE, "Done")
        return self._has_errors

    def _steps(self) -> List[Tuple[Callable[[], None], str]]:
        return [
            (self._adjust_user_attributes, "Set version specific user attributes"),
        ]

    def _initialize_base_environment(self) -> None:
        # Failing to load the config here will result in the loss of *all* services due to (...)
        # EDIT: This is no longer the case; but we probably need the config for other reasons?
        cmk.base.config.load()
        cmk.base.config.load_all_agent_based_plugins(
            cmk.base.check_api.get_check_api_context,
        )

    def _check_failed_gui_plugins(self) -> None:
        failed_plugins = cmk.gui.utils.get_failed_plugins()
        if failed_plugins:
            self._logger.error("")
            self._logger.error(
                "ERROR: Failed to load some GUI plugins. You will either have \n"
                "       to remove or update them to be compatible with this \n"
                "       Checkmk version."
            )
            self._logger.error("")

    def _adjust_user_attributes(self) -> None:
        """All users are loaded and attributes can be transformed or set."""
        users: Users = load_users(lock=True)

        for user_id in users:
            _add_user_scheme_serial(users, user_id)

        save_users(users, datetime.now())


def _format_warning(msg: str) -> str:
    return "\033[93m {}\033[00m".format(msg)


def _add_user_scheme_serial(users: Users, user_id: UserId) -> Users:
    """Set attribute to detect with what cmk version the user was
    created. We start that with 2.0"""
    users[user_id]["user_scheme_serial"] = USER_SCHEME_SERIAL
    return users


def _id_from_title(title: str) -> str:
    return re.sub("[^-a-zA-Z0-9_]+", "", title.lower().replace(" ", "_"))


def _our_logging_level_to_gui_logging_level(lvl: int) -> int:
    """The default in cmk.gui is WARNING, whereas our default is INFO. Hence, our default
    corresponds to INFO in cmk.gui, which results in too much logging.
    """
    return lvl + 10


def main(args: List[str]) -> int:
    arguments = parse_arguments(args)
    log.setup_console_logging()
    log.logger.setLevel(log.verbosity_to_log_level(arguments.verbose))
    logger = logging.getLogger("cmk.update_config")
    if arguments.debug:
        cmk.utils.debug.enable()
    logger.debug("parsed arguments: %s", arguments)

    try:
        has_errors = UpdateConfig(logger, arguments).run()
    except Exception:
        if arguments.debug:
            raise
        logger.exception(
            'ERROR: Please repair this and run "cmk-update-config -v" '
            "BEFORE starting the site again."
        )
        return 1
    return 1 if has_errors else 0


def parse_arguments(args: List[str]) -> argparse.Namespace:
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


# RRD migration cleaups


def check_df_includes_use_new_metric() -> None:
    "Check that df.include files can return fs_used metric name"
    df_file = cmk.utils.paths.local_checks_dir / "df.include"
    if df_file.exists():
        with df_file.open("r") as fid:
            r = fid.read()
            mat = re.search("fs_used", r, re.M)
            if not mat:
                msg = (
                    "source: %s\n Returns the wrong perfdata\n" % df_file
                    + "Checkmk 2.0 requires Filesystem check plugins to deliver "
                    '"Used filesystem space" perfdata under the metric name fs_used. '
                    "Your local extension pluging seems to be using the old convention "
                    "of mountpoints as the metric name. Please update your include file "
                    "to match our reference implementation."
                )
                raise RuntimeError(msg)
