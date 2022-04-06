#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.store as store
from cmk.utils.type_defs import TimeperiodSpec, TimeperiodSpecs

from cmk.gui.globals import active_config
from cmk.gui.hooks import request_memoize
from cmk.gui.i18n import _
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.utils import wato_root_dir


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
    timeperiods = load_timeperiods()
    return timeperiods[name]


def save_timeperiods(timeperiods: TimeperiodSpecs) -> None:
    store.mkdir(wato_root_dir())
    store.save_to_mk_file(
        wato_root_dir() + "timeperiods.mk",
        "timeperiods",
        _filter_builtin_timeperiods(timeperiods),
        pprint_value=active_config.wato_pprint_config,
    )
    load_timeperiods.cache_clear()


def save_timeperiod(name, timeperiod) -> None:
    existing_timeperiods = load_timeperiods()
    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods)


def verify_timeperiod_name_exists(name):
    existing_timperiods = load_timeperiods()
    return name in existing_timperiods


def _filter_builtin_timeperiods(timeperiods: TimeperiodSpecs) -> TimeperiodSpecs:
    builtin_keys = set(builtin_timeperiods().keys())
    return {k: v for k, v in timeperiods.items() if k not in builtin_keys}


class TimeperiodSelection(DropdownChoice):
    def __init__(self, **kwargs):
        kwargs.setdefault("no_preselect_title", _("Select a timeperiod"))
        DropdownChoice.__init__(self, choices=self._get_choices, **kwargs)

    def _get_choices(self):
        timeperiods = load_timeperiods()
        elements = [(name, "%s - %s" % (name, tp["alias"])) for (name, tp) in timeperiods.items()]

        always = ("24X7", _("Always"))
        if always[0] not in dict(elements):
            elements.insert(0, always)

        return sorted(elements, key=lambda x: x[1].lower())
