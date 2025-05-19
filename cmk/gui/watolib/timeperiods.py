#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.user import UserId

from cmk.utils.timeperiod import (
    add_builtin_timeperiods,
    cleanup_timeperiod_caches,
    is_builtin_timeperiod,
    remove_builtin_timeperiods,
    timeperiod_spec_alias,
    TimeperiodName,
    TimeperiodSpec,
    TimeperiodSpecs,
)

from cmk.gui.hooks import request_memoize
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir

from . import changes as _changes

TIMEPERIOD_ID_PATTERN = r"^[-a-z0-9A-Z_]+\Z"
TimeperiodUsage = tuple[str, str]

TimeperiodUsageFinder = Callable[[str], list[TimeperiodUsage]]


# The WatoConfigFile hierarchy is broken in many ways regarding typing, so we have to add some
# typing wrapper methods below.
class TimePeriodsConfigFile(WatoSimpleConfigFile[TimeperiodSpec]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "timeperiods.mk",
            config_variable="timeperiods",
            spec_class=TimeperiodSpec,
        )

    def load_timeperiod_specs_for_reading(self) -> TimeperiodSpecs:
        return {TimeperiodName(n): s for n, s in self.load_for_reading().items()}

    def load_timeperiod_specs_for_modification(self) -> dict[TimeperiodName, TimeperiodSpec]:
        return {TimeperiodName(n): s for n, s in self.load_for_modification().items()}

    def save_timeperiod_specs(self, timeperiods: TimeperiodSpecs, pprint_value: bool) -> None:
        self.save({_project(n): s for n, s in timeperiods.items()}, pprint_value)


# basically the inverse of TimeperiodName
def _project(name: TimeperiodName) -> str:
    return name


# NOTE: This is a variation of cmk.utils.timeperiod.load_timeperiods(). Can we somehow unify this?
@request_memoize()
def load_timeperiods() -> TimeperiodSpecs:
    return add_builtin_timeperiods(TimePeriodsConfigFile().load_timeperiod_specs_for_reading())


def save_timeperiods(timeperiods: TimeperiodSpecs, pprint_value: bool) -> None:
    TimePeriodsConfigFile().save_timeperiod_specs(
        remove_builtin_timeperiods(timeperiods), pprint_value
    )
    cleanup_timeperiod_caches()
    load_timeperiods.cache_clear()  # type: ignore[attr-defined]


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


def load_timeperiod(name: TimeperiodName) -> TimeperiodSpec:
    try:
        timeperiod = load_timeperiods()[name]
    except KeyError:
        raise TimePeriodNotFoundError
    return timeperiod


def delete_timeperiod(
    name: TimeperiodName,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    if is_builtin_timeperiod(name):
        raise TimePeriodBuiltInError()
    time_periods = TimePeriodsConfigFile().load_timeperiod_specs_for_modification()
    if name not in time_periods:
        raise TimePeriodNotFoundError
    if usages := list(find_usages_of_timeperiod(name)):
        raise TimePeriodInUseError(usages=usages)
    del time_periods[name]
    save_timeperiods(time_periods, pprint_value)
    _changes.add_change(
        action_name="edit-timeperiods",
        text=_("Deleted time period %s") % name,
        user_id=user_id,
        use_git=use_git,
    )


def modify_timeperiod(
    name: TimeperiodName,
    timeperiod: TimeperiodSpec,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    if is_builtin_timeperiod(name):
        raise TimePeriodBuiltInError()

    existing_timeperiods = TimePeriodsConfigFile().load_timeperiod_specs_for_modification()
    if name not in existing_timeperiods:
        raise TimePeriodNotFoundError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods, pprint_value)
    _changes.add_change(
        action_name="edit-timeperiods",
        text=_("Modified time period %s") % name,
        user_id=user_id,
        use_git=use_git,
    )


def create_timeperiod(
    name: TimeperiodName,
    timeperiod: TimeperiodSpec,
    *,
    user_id: UserId | None,
    pprint_value: bool,
    use_git: bool,
) -> None:
    if is_builtin_timeperiod(name):
        raise TimePeriodBuiltInError()

    existing_timeperiods = TimePeriodsConfigFile().load_timeperiod_specs_for_modification()
    if name in existing_timeperiods:
        raise TimePeriodAlreadyExistsError()

    existing_timeperiods[name] = timeperiod
    save_timeperiods(existing_timeperiods, pprint_value)
    _changes.add_change(
        action_name="edit-timeperiods",
        text=_("Created new time period %s") % name,
        user_id=user_id,
        use_git=use_git,
    )


def verify_timeperiod_name_exists(name: str) -> bool:
    existing_timperiods = load_timeperiods()
    return name in existing_timperiods


class TimeperiodSelection(DropdownChoice[str]):
    def __init__(
        self,
        title: str | None = None,
        help: str | None = None,
    ) -> None:
        super().__init__(
            choices=self._get_choices,
            title=title,
            help=help,
            no_preselect_title=_("Select a time period"),
        )

    def _get_choices(self) -> list[tuple[str, str]]:
        timeperiods = load_timeperiods()
        elements = [
            (name, "{} - {}".format(name, tp["alias"])) for (name, tp) in timeperiods.items()
        ]

        always = (TimeperiodName("24X7"), _("Always"))
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
    for tpn, tp in load_timeperiods().items():
        if time_period_name in tp.get("exclude", []):
            used_in.append(
                (
                    "{}: {} ({})".format(
                        _("Time period"), timeperiod_spec_alias(tp, tpn), _("excluded")
                    ),
                    makeuri_contextless(
                        request, [("mode", "edit_timeperiod"), ("edit", tpn)], filename="wato.py"
                    ),
                )
            )
    return used_in
