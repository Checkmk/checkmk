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
import os
import subprocess
import sys
import traceback
from collections.abc import Callable, Generator, Sequence
from contextlib import contextmanager
from itertools import chain
from typing import Literal

from cmk.ccc import debug, tty
from cmk.ccc.version import Edition, edition

from cmk.utils import log, paths
from cmk.utils.log import VERBOSE
from cmk.utils.paths import check_mk_config_dir
from cmk.utils.plugin_loader import load_plugins_with_exceptions
from cmk.utils.redis import disable_redis

# This special script needs persistence and conversion code from different
# places of Checkmk. We may centralize the conversion and move the persistance
# to a specific layer in the future, but for the the moment we need to deal
# with it.
from cmk.base import config as base_config

from cmk.gui import main_modules
from cmk.gui.exceptions import MKUserError
from cmk.gui.log import logger as gui_logger
from cmk.gui.session import SuperUserContext
from cmk.gui.site_config import is_wato_slave_site
from cmk.gui.utils import get_failed_plugins
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.automations import ENV_VARIABLE_FORCE_CLI_INTERFACE
from cmk.gui.watolib.changes import ActivateChangesWriter, add_change
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.plugins.pre_actions.utils import ConflictMode

from .registry import pre_update_action_registry, update_action_registry


def main(
    args: Sequence[str], ensure_site_is_stopped_callback: Callable[[logging.Logger], None]
) -> int:
    arguments = _parse_arguments(args)

    if arguments.debug:
        debug.enable()

    logger = _setup_logging(arguments.verbose)
    logger.debug("parsed arguments: %s", arguments)

    if not arguments.site_may_run:
        ensure_site_is_stopped_callback(logger)

    logger.info(
        "%sATTENTION%s\n  Some steps may take a long time depending "
        "on your installation.\n  Please be patient.\n",
        tty.yellow,
        tty.normal,
    )
    with _force_automations_cli_interface():
        exit_code = main_check_config(logger, arguments.conflict)
        if exit_code != 0 or arguments.dry_run:
            return exit_code
        return main_update_config(logger, arguments.conflict)


def main_update_config(logger: logging.Logger, conflict: ConflictMode) -> Literal[0, 1]:
    _load_plugins(logger)

    try:
        return update_config(logger)
    except Exception:
        if debug.enabled():
            raise
        logger.exception(
            'ERROR: Please repair this and run "cmk-update-config" BEFORE starting the site again.'
        )
        return 1


def main_check_config(logger: logging.Logger, conflict: ConflictMode) -> Literal[0, 1]:
    _load_pre_plugins()
    try:
        # This has to be done BEFORE initializing the GUI context on start of
        # the pre update actions
        _cleanup_precompiled_files(logger)

        check_config(logger, conflict)
    except Exception as e:
        if not isinstance(e, MKUserError):
            traceback.print_exc()
        sys.stderr.write(
            f"\nUpdate aborted with Error: {e}.\nYour site has not been modified.\n"
            "The update can be retried after the error has been fixed.\n"
        )
        return 1
    return 0


def _cleanup_precompiled_files(logger: logging.Logger) -> None:
    logger.info("Cleanup precompiled host and folder files")
    for p in (check_mk_config_dir / "wato").glob("**/*.pkl"):
        p.unlink(missing_ok=True)


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
            f"With '{ConflictMode.FORCE}', '{ConflictMode.INSTALL}' or '{ConflictMode.KEEP_OLD}' no interaction is needed. "
            f"'{ConflictMode.FORCE}' continues the update even if errors occur during the pre-flight checks. "
            f"If you choose '{ConflictMode.ABORT}', the update will be aborted if interaction is needed."
        ),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Executes `Verifying Checkmk configuration` only.",
    )
    p.add_argument(
        "--site-may-run",
        action="store_true",
        help="Execute the command even if the site is running.",
    )
    return p.parse_args(args)


# TODO: Fix this cruel hack caused by our funny mix of GUI + console stuff.
def _setup_logging(verbose: int) -> logging.Logger:
    log.logger.setLevel(log.verbosity_to_log_level(verbose))

    logger = logging.getLogger("cmk.update_config")
    logger.setLevel(log.logger.level)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logging.getLogger().addHandler(handler)

    # Special case for PIL module producing messages like "STREAM b'IHDR' 16 13" in debug level
    logging.getLogger("PIL").setLevel(logging.INFO)

    # The default in cmk.gui is WARNING, whereas our default is INFO. Hence, our
    # default corresponds to INFO in cmk.gui, which results in too much logging.
    gui_logger.setLevel(log.logger.level + 10)

    return logger


def ensure_site_is_stopped(logger: logging.Logger) -> None:
    if (
        subprocess.call(["omd", "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        != 1
    ):
        logger.error(
            "ERROR: The Checkmk site is still running. Please stop the site "
            "before updating the configuration. You can stop the site using 'omd stop'."
        )
        sys.exit(1)


def _load_plugins(logger: logging.Logger) -> None:
    for plugin, exc in chain(
        load_plugins_with_exceptions("cmk.update_config.plugins.actions"),
        (
            []
            if edition(paths.omd_root) is Edition.CRE
            else load_plugins_with_exceptions("cmk.update_config.cee.plugins.actions")
        ),
        (
            load_plugins_with_exceptions("cmk.update_config.cme.plugins.actions")
            if edition(paths.omd_root) is Edition.CME
            else []
        ),
    ):
        logger.error("Error in action plug-in %s: %s\n", plugin, exc)
        if debug.enabled():
            raise exc


def _load_pre_plugins() -> None:
    for plugin, exc in chain(
        load_plugins_with_exceptions("cmk.update_config.plugins.pre_actions"),
        (
            []
            if edition(paths.omd_root) is Edition.CRE
            else load_plugins_with_exceptions("cmk.update_config.cee.plugins.pre_actions")
        ),
    ):
        sys.stderr.write(f"Error in pre action plug-in {plugin}: {exc}\n")
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

    main_modules.load_plugins()

    # Note: Redis has to be disabled first, the other contexts depend on it
    with disable_redis(), gui_context():
        _initialize_base_environment()
        for count, pre_action in enumerate(pre_update_actions, start=1):
            logger.info(f" {tty.yellow}{count:02d}/{total:02d}{tty.normal} {pre_action.title}...")
            pre_action(logger, conflict_mode)

    logger.info(f"Done ({tty.green}success{tty.normal})\n")


def update_config(logger: logging.Logger) -> Literal[0, 1]:
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
                    action(logger)
            except Exception:
                has_errors = True
                logger.error(f' + "{action.title}" failed', exc_info=True)
                if not action.continue_on_failure or debug.enabled():
                    raise

        if not has_errors and not is_wato_slave_site():
            # Force synchronization of the config after a successful configuration update
            add_change(
                action_name="cmk-update-config",
                text="Successfully updated Checkmk configuration",
                user_id=None,
                need_sync=True,
                use_git=False,
            )

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
    base_config.load(discovery_rulesets=())


@contextmanager
def _force_automations_cli_interface() -> Generator[None]:
    try:
        os.environ[ENV_VARIABLE_FORCE_CLI_INTERFACE] = "True"
        yield
    finally:
        os.environ.pop(ENV_VARIABLE_FORCE_CLI_INTERFACE, None)
