#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Tuple as _Tuple

import cmk.utils.store as store
from cmk.utils.type_defs import TimeperiodSpec, TimeperiodSpecs

import cmk.gui.watolib.changes as _changes
from cmk.gui.globals import config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.utils import wato_root_dir

TimeperiodUsage = _Tuple[str, str]


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


def builtin_timeperiods() -> TimeperiodSpecs:
    return {
        "24X7": {
            "alias": _("Always"),
            "monday": [("00:00", "24:00")],
            "tuesday": [("00:00", "24:00")],
            "wednesday": [("00:00", "24:00")],
            "thursday": [("00:00", "24:00")],
            "friday": [("00:00", "24:00")],
            "saturday": [("00:00", "24:00")],
            "sunday": [("00:00", "24:00")],
        }
    }


@request_memoize()
def load_timeperiods() -> TimeperiodSpecs:
    timeperiods = store.load_from_mk_file(wato_root_dir() + "timeperiods.mk", "timeperiods", {})
    timeperiods.update(builtin_timeperiods())
    return timeperiods


def load_timeperiod(name: str) -> TimeperiodSpec:
    try:
        timeperiod = load_timeperiods()[name]
    except KeyError:
        raise TimePeriodNotFoundError
    return timeperiod


def delete_timeperiod(name: str) -> None:
    time_periods = load_timeperiods()
    if name not in time_periods:
        raise TimePeriodNotFoundError
    time_period_details = time_periods[name]
    time_period_alias = time_period_details["alias"]
    # TODO: introduce at least TypedDict for TimeperiodSpecs to remove assertion
    assert isinstance(time_period_alias, str)
    if name in builtin_timeperiods():
        raise TimePeriodBuiltInError()
    del time_periods[name]
    save_timeperiods(time_periods)
    _changes.add_change("edit-timeperiods", _("Deleted time period %s") % name)


def save_timeperiods(timeperiods: TimeperiodSpecs) -> None:
    store.mkdir(wato_root_dir())
    store.save_to_mk_file(
        wato_root_dir() + "timeperiods.mk",
        "timeperiods",
        _filter_builtin_timeperiods(timeperiods),
        pprint_value=config.wato_pprint_config,
    )
    load_timeperiods.cache_clear()


def modify_timeperiod(name: str, timeperiod: TimeperiodSpec) -> None:  # type: ignore[no-untyped-def]
    existing_timeperiods = load_timeperiods()
    if name not in existing_timeperiods:
        raise TimePeriodNotFoundError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)
    _changes.add_change("edit-timeperiods", _("Modified time period %s") % name)


def create_timeperiod(name: str, timeperiod: TimeperiodSpec) -> None:  # type: ignore[no-untyped-def]
    existing_timeperiods = load_timeperiods()
    if name in existing_timeperiods:
        raise TimePeriodAlreadyExistsError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)
    _changes.add_change("edit-timeperiods", _("Created new time period %s") % name)


def verify_timeperiod_name_exists(name):
    existing_timperiods = load_timeperiods()
    return name in existing_timperiods


def _filter_builtin_timeperiods(timeperiods: TimeperiodSpecs) -> TimeperiodSpecs:
    builtin_keys = set(builtin_timeperiods().keys())
    return {k: v for k, v in timeperiods.items() if k not in builtin_keys}


class TimeperiodSelection(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs.setdefault("no_preselect", True)
        kwargs.setdefault("no_preselect_title", _("Select a timeperiod"))
        DropdownChoice.__init__(self, choices=self._get_choices, **kwargs)

    def _get_choices(self):
        timeperiods = load_timeperiods()
        elements = [(name, "%s - %s" % (name, tp["alias"])) for (name, tp) in timeperiods.items()]

        always = ("24X7", _("Always"))
        if always[0] not in dict(elements):
            elements.insert(0, always)

        return sorted(elements, key=lambda x: x[1].lower())
