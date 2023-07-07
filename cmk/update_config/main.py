#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Tool for updating Checkmk configuration files after version updates

This command is normally executed automatically at the end of "omd update" on
all sites and on remote sites after receiving a snapshot and does not need to
be called manually.
"""

import argparse
import logging
import sys
from collections.abc import Sequence
from itertools import chain
from pathlib import Path

from cmk.utils import debug, log, paths, tty
from cmk.utils.log import VERBOSE
from cmk.utils.plugin_loader import load_plugins_with_exceptions
from cmk.utils.redis import disable_redis
from cmk.utils.version import edition, Edition

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
from cmk.base import config as base_config
from cmk.base.check_api import get_check_api_context

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.log import logger as gui_logger
from cmk.gui.session import SuperUserContext
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.changes import ActivateChangesWriter, add_change
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.pre_actions.utils import ConflictMode

from .registry import pre_update_action_registry, update_action_registry
from .update_state import UpdateState


def main(args: Sequence[str]) -> int:
    arguments = _parse_arguments(args)

    if arguments.debug:
        debug.enable()

    logger = _setup_logging(arguments)

    logger.info(
        "%sATTENTION%s\n  Some steps may take a long time depending "
        "on your installation.\n  Please be patient.\n",
        tty.yellow,
        tty.normal,
    )

    _load_pre_plugins()
    try:
        check_config(logger, arguments.conflict)
    except MKUserError as e:
        sys.stderr.write(
            f"\nUpdate aborted: {e}.\n"
            "The Checkmk configuration has not been modified.\n\n"
            "You can downgrade to your previous version again using "
            "'omd update' and start the site again.\n"
        )
        return 1
    except Exception as e:
        if debug.enabled():
            raise
        sys.stderr.write(
            "Unknown error on pre update action.\n"
            f"Error: {e}\n\n"
            "Please repair this and run 'cmk-update-config'"
            "BEFORE starting the site again."
        )
        return 1

    update_state = UpdateState.load(Path(paths.var_dir))
    _load_plugins(logger)

    try:
        return update_config(logger, update_state)
    except Exception:
        if debug.enabled():
            raise
        logger.exception(
            'ERROR: Please repair this and run "cmk-update-config" '
            "BEFORE starting the site again."
        )
        return 1


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
    p.add_argument(
        "--conflict",
        choices=list(ConflictMode),
        default=ConflictMode.ASK,
        type=ConflictMode,
        help=(
            f"If you choose '{ConflictMode.ASK}', you will need to manually answer all upcoming questions. "
            f"With '{ConflictMode.INSTALL}' or '{ConflictMode.KEEP_OLD}' no interaction is needed. "
            f"If you choose '{ConflictMode.ABORT}', the update will be aborted if interaction is needed."
        ),
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
        []
        if edition() is Edition.CRE
        else load_plugins_with_exceptions("cmk.update_config.cee.plugins.actions"),
    ):
        logger.error("Error in action plugin %s: %s\n", plugin, exc)
        if debug.enabled():
            raise exc


def _load_pre_plugins() -> None:
    for plugin, exc in load_plugins_with_exceptions("cmk.update_config.plugins.pre_actions"):
        sys.stderr.write(f"Error in pre action plugin {plugin}: {exc}\n")
        if debug.enabled():
            raise exc


# TODO(sk): check_config can't raise exception(raise is an reaction on check, i.e. 2 in 1):
# change name assert_config or ensure_valid_config for example
# or change logic
def check_config(logger: logging.Logger, conflict_mode: ConflictMode) -> None:
    """Raise exception on failure"""
    pre_update_actions = sorted(pre_update_action_registry.values(), key=lambda a: a.sort_index)
    total = len(pre_update_actions)
    logger.info("Verifying Checkmk configuration...")
    for count, pre_action in enumerate(pre_update_actions, start=1):
        logger.info(f" {tty.yellow}{count:02d}/{total:02d}{tty.normal} {pre_action.title}...")
        pre_action(conflict_mode)

    logger.info(f"Done ({tty.green}success{tty.normal})\n")


def update_config(logger: logging.Logger, update_state: UpdateState) -> int:
    """Return exit code, 0 is ok, 1 is failure"""
    has_errors = False
    logger.log(VERBOSE, "Initializing application...")

    main_modules.load_plugins()

    actions = sorted(update_action_registry.values(), key=lambda a: a.sort_index)
    total = len(actions)

    # Note: Redis has to be disabled first, the other contexts depend on it
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        _check_failed_gui_plugins(logger)
        _initialize_base_environment()

        logger.info("Updating Checkmk configuration...")

        for num, action in enumerate(actions, start=1):
            logger.info(f" {tty.yellow}{num:02d}/{total:02d}{tty.normal} {action.title}...")
            try:
                with ActivateChangesWriter.disable():
                    action(logger, update_state.setdefault(action.name))
            except Exception:
                has_errors = True
                logger.error(f' + "{action.title}" failed', exc_info=True)
                if not action.continue_on_failure or debug.enabled():
                    raise

        if not has_errors and not is_wato_slave_site():
            # Force synchronization of the config after a successful configuration update
            add_change(
                "cmk-update-config",
                "Successfully updated Checkmk configuration",
                need_sync=True,
            )

    update_state.save()

    if has_errors:
        logger.error(f"Done ({tty.red}with errors{tty.normal})")
        return 1

    logger.info(f"Done ({tty.green}success{tty.normal})")
    return 0


def _check_failed_gui_plugins(logger: logging.Logger) -> None:
    if get_failed_plugins():
        logger.error(
            "\n"
            "ERROR: Failed to load some GUI plugins. You will either have \n"
            "       to remove or update them to be compatible with this \n"
            "       Checkmk version."
            "\n"
        )


def _initialize_base_environment() -> None:
    base_config.load_all_agent_based_plugins(
        get_check_api_context,
        local_checks_dir=paths.local_checks_dir,
        checks_dir=paths.checks_dir,
    )
    # Watch out: always load the plugins before loading the config.
    # The validation step will not be executed otherwise.
    base_config.load()
