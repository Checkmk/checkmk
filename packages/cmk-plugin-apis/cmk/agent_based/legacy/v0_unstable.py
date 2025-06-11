#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Anys all over the place :-(
# mypy: disable-error-code="misc"

"""
The things in this module specify the old Check_MK (<- see? Old!) check API

+---------------------------------------------------------------------------+
|             THIS API IS OLD, AND NO LONGER MAINTAINED.                    |
|                                                                           |
| Plugins programmed against this API are only considered, if they reside   |
| in the checks_dir (share/check_mk/checks).                                |
|                                                                           |
|       !!   Files in the local hierarchy are NOT CONSIDERED     !!         |
|                                                                           |
| This implies that these plugins can not be distributed in an MKP!         |
|                                                                           |
| All new plugins should be programmed against the new API, please refer to |
| the online user manual for details!                                       |
|                                                                           |
+---------------------------------------------------------------------------+

"""

from collections.abc import Callable, Generator, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based import v1 as _v1
from cmk.agent_based.v2 import (
    DiscoveryResult,
    IgnoreResults,
    Metric,
    Result,
    SNMPDetectSpecification,
    SNMPTree,
)

__all__ = [
    "check_levels",
    "LegacyCheckDefinition",
    "LegacyCheckResult",
    "LegacyDiscoveryResult",
    "LegacyResult",
    "LegacyService",
    "passwordstore_get_cmdline",
    "STATE_MARKERS",
]

_DiscoveredParameters = Mapping | tuple | str | None  # type: ignore[type-arg]


_DiscoveryFunctionLegacy = Callable[..., None | Iterable[tuple[str | None, _DiscoveredParameters]]]  # type: ignore[explicit-any]
_DiscoveryFunctionV2Compliant = Callable[..., DiscoveryResult]  # type: ignore[explicit-any]

_OptNumber = None | int | float

_MetricTupleMinimal = tuple[str, float]
_MetricTupleWithLevels = tuple[str, float, _OptNumber, _OptNumber]
_MetricTupleWithLevelsAndBoundary = tuple[
    str, float, _OptNumber, _OptNumber, _OptNumber, _OptNumber
]


# there are for more variants than these, but let's keep it as 'simple' as possible.
LegacyResult = (
    tuple[int, str]
    | tuple[
        int,
        str,
        list[_MetricTupleMinimal]
        | list[_MetricTupleWithLevels]
        | list[_MetricTupleWithLevelsAndBoundary],
    ]
)


_CheckFunctionLegacy = Callable[  # type: ignore[explicit-any]
    ...,
    None | LegacyResult | Iterable[LegacyResult] | Generator[LegacyResult, None, None],
]
_CheckFunctionV2Compliant = Callable[..., Generator[Result | Metric | IgnoreResults, None, None]]  # type: ignore[explicit-any]


@dataclass(frozen=True, kw_only=True)
class LegacyCheckDefinition:  # type: ignore[explicit-any]
    name: str
    detect: SNMPDetectSpecification | None = None
    fetch: list[SNMPTree] | SNMPTree | None = None
    sections: list[str] | None = None
    check_function: _CheckFunctionV2Compliant | _CheckFunctionLegacy | None = None
    discovery_function: _DiscoveryFunctionV2Compliant | _DiscoveryFunctionLegacy | None = None
    parse_function: Callable[[list], object] | None = None  # type: ignore[type-arg]
    check_ruleset_name: str | None = None
    check_default_parameters: Mapping[str, Any] | None = None  # type: ignore[explicit-any]
    service_name: str | None = None


STATE_MARKERS = ("", "(!)", "(!!)", "(?)")

_Levels = tuple  # type: ignore[type-arg] # Has length 2 or 4

LegacyCheckResult = Generator[LegacyResult, None, None]

LegacyService = tuple[str | None, Mapping[str, object]]
LegacyDiscoveryResult = Iterable[LegacyService]


def _normalize_levels(levels: _Levels) -> _Levels:
    if len(levels) == 2:  # upper warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = None, None

    else:  # upper and lower warn and crit
        warn_upper, crit_upper = levels[0], levels[1]
        warn_lower, crit_lower = levels[2], levels[3]

    return warn_upper, crit_upper, warn_lower, crit_lower


def _do_check_levels(
    value: int | float,
    levels: _Levels,
    human_readable_func: Callable,  # type: ignore[type-arg]
) -> tuple[int, str]:
    warn_upper, crit_upper, warn_lower, crit_lower = _normalize_levels(levels)
    # Critical cases
    if crit_upper is not None and value >= crit_upper:
        return 2, _levelsinfo_ty("at", warn_upper, crit_upper, human_readable_func)
    if crit_lower is not None and value < crit_lower:
        return 2, _levelsinfo_ty("below", warn_lower, crit_lower, human_readable_func)

    # Warning cases
    if warn_upper is not None and value >= warn_upper:
        return 1, _levelsinfo_ty("at", warn_upper, crit_upper, human_readable_func)
    if warn_lower is not None and value < warn_lower:
        return 1, _levelsinfo_ty("below", warn_lower, crit_lower, human_readable_func)
    return 0, ""


def _levelsinfo_ty(
    ty: str,
    warn: _OptNumber,
    crit: _OptNumber,
    human_readable_func: Callable,  # type: ignore[type-arg]
) -> str:
    warn_str = "never" if warn is None else f"{human_readable_func(warn)}"
    crit_str = "never" if crit is None else f"{human_readable_func(crit)}"
    return f" (warn/crit {ty} {warn_str}/{crit_str})"


def _build_perfdata(
    dsname: None | str,
    value: int | float,
    levels: _Levels,
    boundaries: tuple | None,  # type: ignore[type-arg]
) -> list:  # type: ignore[type-arg]
    if not dsname:
        return []
    used_boundaries = boundaries if isinstance(boundaries, tuple) and len(boundaries) == 2 else ()
    return [(dsname, value, levels[0], levels[1], *used_boundaries)]


def check_levels(  # type: ignore[explicit-any]
    value: int | float,
    dsname: None | str,
    params: Any,
    unit: str = "",
    human_readable_func: Callable | None = None,  # type: ignore[type-arg]
    infoname: str | None = None,
    boundaries: tuple[float | None, float | None] | None = None,
) -> tuple[int, str, list[_MetricTupleWithLevelsAndBoundary]]:
    """Generic function for checking a value against levels

    This also supports predictive levels.

    value:   currently measured value
    dsname:  name of the datasource in the RRD that corresponds to this value
             or None in order to skip perfdata
    params:  None or Tuple(None, None) -> no level checking.
             Tuple variants with non-None values:
             Tuple[warn_upper, crit_upper] -> upper level checking only.
             Tuple[warn_upper, crit_upper, warn_lower, crit_lower]
             -> upper and lower level checking.
             If a Dict is passed to check_levels, predictive levels are used
             automatically. The following constellations are possible:
             Dict containing "lower" as key -> lower level checking.
             Dict containing "upper" or "levels_upper_min" as key -> upper level checking.
             Dict containing "lower" and "upper"/"levels_upper_min" as key ->
             lower and upper level checking.
    unit:    unit to be displayed in the plug-in output.
             Be aware: if a (builtin) human_readable_func is stated which already
             provides a unit info, then this unit is not necessary. An additional
             unit info is useful if a rate is calculated, eg.
                unit="/s",
                human_readable_func=get_bytes_human_readable,
             results in 'X B/s'.
    human_readable_func: Single argument function to present in a human readable fashion
                         the value. Builtin human_readable-functions already provide a unit:
                         - get_percent_human_readable
                         - get_age_human_readable
                         - get_bytes_human_readable
                         - get_filesize_human_readable
                         - get_nic_speed_human_readable
                         - get_timestamp_human_readable
                         - get_relative_date_human_readable
    infoname: Perf value name for infotext like a title.
    boundaries: Add minimum and maximum to performance data.
    """
    if unit.startswith("/"):
        unit_info: str = unit
    elif unit:
        unit_info = " %s" % unit
    else:
        unit_info = ""

    if human_readable_func is None:

        def render_func(x: float) -> str:
            return f"{x:.2f}{unit_info}"

    else:

        def render_func(x: float) -> str:
            return f"{human_readable_func(x)}{unit_info}"

    if params and isinstance(params, dict):
        if not dsname:
            raise TypeError("Metric name is empty/None")
        result, *metrics = _v1.check_levels_predictive(
            value,
            levels=params,
            metric_name=dsname,
            render_func=render_func,
            label=infoname,
            boundaries=boundaries,
        )
        assert isinstance(result, _v1.Result)
        return (
            int(result.state),
            result.summary,
            [
                (m.name, m.value, *m.levels, *m.boundaries)
                for m in metrics
                if isinstance(m, _v1.Metric)
            ],
        )

    infotext = f"{render_func(value)}"
    if infoname:
        infotext = f"{infoname}: {infotext}"

    # normalize {}, (), None, (None, None), (None, None, None, None)
    if not params or set(params) <= {None}:
        levels: _Levels = (None, None, None, None)
    else:
        levels = _normalize_levels(params)

    state, levelstext = _do_check_levels(value, levels, render_func)
    return state, infotext + levelstext, _build_perfdata(dsname, value, levels, boundaries)


def passwordstore_get_cmdline(fmt: str, pw: tuple | str) -> str | tuple[str, str, str]:  # type: ignore[type-arg]
    """Use this to prepare a command line argument for using a password from the
    Check_MK password store or an explicitly configured password."""
    if not isinstance(pw, tuple):
        pw = ("password", pw)

    if pw[0] == "password":
        return str(fmt % pw[1])

    return ("store", pw[1], fmt)
