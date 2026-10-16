#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Warn about the base config files that still need pre-seeded variables

Checkmk 3.1 executes main.mk, the files below conf.d, final.mk and
local.mk without predefined variables: every file must define the variables it extends
itself (see ``cmk.ccc.store.bootstrap_statement``). The update rewrites
the files Checkmk generates; this action, run after all of them, loads
each file on its own through the config loader and names the
hand-written ones that still depend on the pre-seeded variables:

* the files that cannot be loaded into a namespace that starts out empty
* the files that load, but end up with a different value for a
  configuration variable than they do with the pre-seeded defaults. Such
  a file extends a variable whose default is not empty, e.g.
  ``alert_handler_event_types += ['checkresult']``: without the default
  it would silently drop it.

In 3.0 that is a warning: the site still loads its configuration with
the pre-seeded variables.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from logging import Logger
from pathlib import Path
from typing import override

from cmk.base.config import (
    ConfigFileLoadError,
    get_config_file_paths,
    load_raw_config,
)
from cmk.config import get_legacy_default_base_config
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry


@dataclass(frozen=True)
class UnseededConfigFindings:
    unloadable: Sequence[tuple[Path, BaseException]]
    """The files that fail to load without predefined variables, and their error"""
    relying_on_defaults: Sequence[tuple[Path, Sequence[str]]]
    """The files that load, and the variables they end up with a different value for"""


def check_config_files() -> UnseededConfigFindings:
    """Load each base config file on its own, with and without the predefined defaults

    Every file must define what it extends, even if another file defines it.
    """
    variables = get_legacy_default_base_config().keys()
    unloadable: list[tuple[Path, BaseException]] = []
    relying_on_defaults: list[tuple[Path, Sequence[str]]] = []
    for path in get_config_file_paths(with_conf_d=True):
        try:
            unseeded = load_raw_config(config_files=[path], context_factory=dict)
        except ConfigFileLoadError as e:
            unloadable.append((e.path, e.__cause__ or e))
            continue

        try:
            seeded = load_raw_config(config_files=[path])
        except ConfigFileLoadError:
            continue  # fails entirely anyway, nothing to compare

        if differing := sorted(
            name for name in unseeded.keys() & variables if unseeded[name] != seeded[name]
        ):
            relying_on_defaults.append((path, differing))
    return UnseededConfigFindings(unloadable=unloadable, relying_on_defaults=relying_on_defaults)


class VerifyUnseededBaseConfig(UpdateAction):
    """Warn about the config files that still need pre-seeded variables"""

    @override
    def __call__(self, logger: Logger) -> None:
        findings = check_config_files()
        if findings.unloadable:
            _warn_unloadable(logger, findings.unloadable)
        if findings.relying_on_defaults:
            _warn_relying_on_defaults(logger, findings.relying_on_defaults)


_LOG_PREFIX = " " * 7


def _warn_unloadable(logger: Logger, failures: Sequence[tuple[Path, BaseException]]) -> None:
    logger.warning(
        "\n%(log_prefix)sSome of your configuration files cannot be loaded without predefined\n"
        "%(log_prefix)svariables.\n\n"
        "%(log_prefix)sCheckmk 3.0 still predefines every configuration variable before loading\n"
        "%(log_prefix)smain.mk, the files below conf.d, final.mk and local.mk. Checkmk 3.1 will\n"
        "%(log_prefix)snot, and the update to 3.1 will fail on the files listed below.\n\n"
        "%(log_prefix)sMost likely such a file extends a variable it does not define itself\n"
        "%(log_prefix)s(defining it in another file is not enough), and the error reads\n"
        "%(log_prefix)s\"name '...' is not defined\". Define each variable before extending it,\n"
        "%(log_prefix)se.g. `x = locals().setdefault('x', {})` for a dict,\n"
        "%(log_prefix)s`x = locals().setdefault('x', [])` for a list or\n"
        "%(log_prefix)s`x = locals().setdefault('x', '')` for a string.\n"
        "%(log_prefix)sIf the default of the variable is not empty, assign its complete value\n"
        "%(log_prefix)sinstead: the line above would drop the default in Checkmk 3.1.\n\n"
        "%(log_prefix)sThe following configuration files fail to load:\n",
        {"log_prefix": _LOG_PREFIX},
    )
    for path, exc in failures:
        logger.warning(
            "%(log_prefix)s  %(path)s: %(error)s",
            {"log_prefix": _LOG_PREFIX, "path": path, "error": exc},
        )


def _warn_relying_on_defaults(
    logger: Logger, findings: Sequence[tuple[Path, Sequence[str]]]
) -> None:
    logger.warning(
        "\n%(log_prefix)sSome of your configuration files extend variables whose default is\n"
        "%(log_prefix)snot empty.\n\n"
        "%(log_prefix)sCheckmk 3.0 still predefines every configuration variable with its\n"
        "%(log_prefix)sdefault, so such a file adds to the default. Checkmk 3.1 will not, and\n"
        "%(log_prefix)sthe file will replace the default by what it adds. For example\n"
        "%(log_prefix)s`alert_handler_event_types += ['checkresult']` would stop the alerts on\n"
        "%(log_prefix)sstate changes. Assign the complete value instead, e.g.\n"
        "%(log_prefix)s`alert_handler_event_types = ['statechange', 'checkresult']`.\n\n"
        "%(log_prefix)sThe following configuration files rely on the defaults of these variables:\n",
        {"log_prefix": _LOG_PREFIX},
    )
    for path, variables in findings:
        logger.warning(
            "%(log_prefix)s  %(path)s: %(variables)s",
            {"log_prefix": _LOG_PREFIX, "path": path, "variables": ", ".join(variables)},
        )


update_action_registry.register(
    VerifyUnseededBaseConfig(
        name="verify_unseeded_base_config",
        title="Verifying the configuration files load without predefined variables",
        sort_index=997,  # after every action that rewrites .mk files
        expiry_version=ExpiryVersion.CMK_310,
        continue_on_failure=True,
    )
)
