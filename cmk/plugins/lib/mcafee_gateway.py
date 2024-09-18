#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import datetime
import typing

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v1 import check_levels_predictive
from cmk.agent_based.v2 import any_of, CheckResult, contains, get_rate, GetRateError, Result, State

DETECT_EMAIL_GATEWAY = contains(".1.3.6.1.2.1.1.1.0", "mcafee email gateway")
DETECT_MCAFEE_WEBGATEWAY = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "mcafee web gateway"),
    contains(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.1230.2.7.1.1"),
)
DETECT_SKYHIGH_WEBGATEWAY = any_of(
    contains(".1.3.6.1.2.1.1.1.0", "skyhigh secure web gateway"),
    contains(".1.3.6.1.2.1.1.2.0", "1.3.6.1.4.1.59732.2.7.1.1"),
)

ValueStore = typing.MutableMapping[str, typing.Any]

PredictiveLevels = dict[str, object] | tuple[float, float] | None


class MiscParams(typing.TypedDict, total=True):
    clients: tuple[int, int] | None
    network_sockets: tuple[int, int] | None
    time_to_resolve_dns: tuple[int, int] | None
    time_consumed_by_rule_engine: tuple[int, int] | None
    client_requests_http: PredictiveLevels
    client_requests_httpv2: PredictiveLevels
    client_requests_https: PredictiveLevels


MISC_DEFAULT_PARAMS = MiscParams(
    clients=None,
    network_sockets=None,
    time_to_resolve_dns=(1500, 2000),
    time_consumed_by_rule_engine=(1500, 2000),
    client_requests_http=(500, 1000),
    client_requests_httpv2=(500, 1000),
    client_requests_https=(500, 1000),
)


@dataclasses.dataclass
class Section:
    """section: webgateway (mcafee_webgateway, skyhigh_security_webgateway)"""

    client_count: int | None
    socket_count: int | None
    time_to_resolve_dns: datetime.timedelta | None
    time_consumed_by_rule_engine: datetime.timedelta | None


def get_param_in_seconds(param: tuple[int, int] | None) -> tuple[float, float] | None:
    """Time is specified in milliseconds.

    >>> get_param_in_seconds((100, 200))
    (0.1, 0.2)
    """
    if param is None:
        return None
    return param[0] / 1000, param[1] / 1000


def compute_rate(
    now: float,
    value_store: ValueStore,
    value: int | None,
    metric_name: str,
    levels: PredictiveLevels,
    key: str,
    label: str | None = None,
) -> CheckResult:
    if value is None:
        return
    try:
        rate = get_rate(value_store, key, now, value)
    except GetRateError:
        yield Result(state=State.OK, summary="Can't compute rate.")
        return
    if isinstance(levels, dict):
        yield from check_levels_predictive(
            rate,
            metric_name=metric_name,
            levels=levels,
            render_func=lambda f: "%.1f/s" % f,
            label=label,
        )
    else:
        yield from check_levels_v1(
            rate,
            metric_name=metric_name,
            levels_upper=levels,
            render_func=lambda f: "%.1f/s" % f,
            label=label,
        )
