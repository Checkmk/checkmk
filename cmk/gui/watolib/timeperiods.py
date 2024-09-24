#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Callable

import cmk.utils.store as store
from cmk.utils.plugin_registry import Registry
from cmk.utils.timeperiod import (
    builtin_timeperiods,
    load_timeperiods,
    timeperiod_spec_alias,
    TimeperiodSpec,
    TimeperiodSpecs,
)

from cmk.gui.config import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import DropdownChoice

from . import changes as _changes
from .utils import wato_root_dir

TIMEPERIOD_ID_PATTERN = r"^[-a-z0-9A-Z_]+\Z"
TimeperiodUsage = tuple[str, str]

TimeperiodUsageFinder = Callable[[str], list[TimeperiodUsage]]


class TimeperiodUsageFinderRegistry(Registry[TimeperiodUsageFinder]):
    def plugin_name(self, instance: TimeperiodUsageFinder) -> str:
        return instance.__name__


timeperiod_usage_finder_registry = TimeperiodUsageFinderRegistry()


class TimePeriodNotFoundError(KeyError):
    pass


class TimePeriodAlreadyExistsError(KeyError):
    pass


class TimePeriodBuiltInError(Exception):
    pass


class TimePeriodInUseError(Exception):
    def __init__(self, usages: list[TimeperiodUsage]) -> None:
        super().__init__()
        self.usages = usages


@request_memoize()
def _load_timeperiods() -> TimeperiodSpecs:
    return load_timeperiods()


def load_timeperiod(name: str) -> TimeperiodSpec:
    try:
        timeperiod = _load_timeperiods()[name]
    except KeyError:
        raise TimePeriodNotFoundError
    return timeperiod


def delete_timeperiod(name: str) -> None:
    if name in builtin_timeperiods():
        raise TimePeriodBuiltInError()
    time_periods = _load_timeperiods()
    if name not in time_periods:
        raise TimePeriodNotFoundError
    if usages := list(find_usages_of_timeperiod(name)):
        raise TimePeriodInUseError(usages=usages)
    del time_periods[name]
    save_timeperiods(time_periods)
    _changes.add_change("edit-timeperiods", _("Deleted time period %s") % name)


def save_timeperiods(timeperiods: TimeperiodSpecs) -> None:
    store.mkdir(wato_root_dir())
    store.save_to_mk_file(
        wato_root_dir() + "timeperiods.mk",
        "timeperiods",
        _filter_builtin_timeperiods(timeperiods),
        pprint_value=active_config.wato_pprint_config,
    )
    _load_timeperiods.cache_clear()  # type: ignore[attr-defined]


def modify_timeperiod(name: str, timeperiod: TimeperiodSpec) -> None:  # type: ignore[no-untyped-def]
    existing_timeperiods = _load_timeperiods()
    if name not in existing_timeperiods:
        raise TimePeriodNotFoundError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)
    _changes.add_change("edit-timeperiods", _("Modified time period %s") % name)


def create_timeperiod(name: str, timeperiod: TimeperiodSpec) -> None:  # type: ignore[no-untyped-def]
    existing_timeperiods = _load_timeperiods()
    if name in existing_timeperiods:
        raise TimePeriodAlreadyExistsError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)
    _changes.add_change("edit-timeperiods", _("Created new time period %s") % name)


def verify_timeperiod_name_exists(name):
    existing_timperiods = _load_timeperiods()
    return name in existing_timperiods


def _filter_builtin_timeperiods(timeperiods: TimeperiodSpecs) -> TimeperiodSpecs:
    builtin_keys = set(builtin_timeperiods().keys())
    return {k: v for k, v in timeperiods.items() if k not in builtin_keys}


class TimeperiodSelection(DropdownChoice[str]):
    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        kwargs.setdefault("no_preselect_title", _("Select a time period"))
        super().__init__(choices=self._get_choices, **kwargs)

    def _get_choices(self) -> list[tuple[str, str]]:
        timeperiods = _load_timeperiods()
        elements = [
            (name, "{} - {}".format(name, tp["alias"])) for (name, tp) in timeperiods.items()
        ]

        always = ("24X7", _("Always"))
        if always[0] not in dict(elements):
            elements.insert(0, always)

        return sorted(elements, key=lambda x: x[1].lower())


def find_usages_of_timeperiod(time_period_name: str) -> list[TimeperiodUsage]:
    """Find all usages of a timeperiod

    Possible usages:
     - 1. rules: service/host-notification/check-period
     - 2. user accounts (notification period)
     - 3. excluded by other time periods
     - 4. time period condition in notification and alerting rules
     - 5. bulk operation in notification rules
     - 6. time period condition in EC rules
     - 7. rules: time specific parameters
    """
    used_in: list[TimeperiodUsage] = []
    for finder in timeperiod_usage_finder_registry.values():
        used_in += finder(time_period_name)
    used_in += _find_usages_in_other_timeperiods(time_period_name)
    return used_in


def _find_usages_in_other_timeperiods(time_period_name: str) -> list[TimeperiodUsage]:
    used_in: list[TimeperiodUsage] = []
    for tpn, tp in _load_timeperiods().items():
        if time_period_name in tp.get("exclude", []):
            used_in.append(
                (
                    "{}: {} ({})".format(
                        _("Time period"), timeperiod_spec_alias(tp, tpn), _("excluded")
                    ),
                    makeuri_contextless(
                        request,
                        [("mode", "edit_timeperiod"), ("edit", tpn)],
                        filename="wato.py",
                    ),
                )
            )
    return used_in
