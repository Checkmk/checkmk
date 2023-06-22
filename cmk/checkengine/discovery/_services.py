#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections.abc import Container, Iterable, Sequence

from cmk.checkengine.checking import CheckPluginName

from ._autochecks import AutocheckEntry
from ._utils import QualifiedDiscovery

__all__ = ["analyse_services"]


def analyse_services(
    *,
    existing_services: Sequence[AutocheckEntry],
    discovered_services: Iterable[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
    keep_vanished: bool,
) -> QualifiedDiscovery[AutocheckEntry]:
    return QualifiedDiscovery(
        preexisting=list(
            _services_to_remember(
                choose_from=existing_services,
                run_plugin_names=run_plugin_names,
                forget_existing=forget_existing,
            )
        ),
        current=list(
            itertools.chain(
                discovered_services,
                _services_to_keep(
                    choose_from=existing_services,
                    run_plugin_names=run_plugin_names,
                    keep_vanished=keep_vanished,
                ),
            )
        ),
    )


def _services_to_remember(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    forget_existing: bool,
) -> Iterable[AutocheckEntry]:
    """Compile a list of services to regard as being the last known state

    This list is used to classify services into new/old/vanished.
    Remembering is not the same as keeping!
    Always remember the services of plugins that are not being run.
    """
    return _drop_plugins_services(choose_from, run_plugin_names) if forget_existing else choose_from


def _services_to_keep(
    *,
    choose_from: Sequence[AutocheckEntry],
    run_plugin_names: Container[CheckPluginName],
    keep_vanished: bool,
) -> Iterable[AutocheckEntry]:
    """Compile a list of services to keep in addition to the discovered ones

    These services are considered to be currently present (even if they are not discovered).
    Always keep the services of plugins that are not being run.
    """
    return (
        list(choose_from)
        if keep_vanished
        else _drop_plugins_services(choose_from, run_plugin_names)
    )


def _drop_plugins_services(
    services: Sequence[AutocheckEntry],
    plugin_names: Container[CheckPluginName],
) -> Iterable[AutocheckEntry]:
    return (s for s in services if s.check_plugin_name not in plugin_names)
