#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import datetime
import typing

from cmk.base.plugins.agent_based.agent_based_api import v1

DETECT_EMAIL_GATEWAY = v1.contains(".1.3.6.1.2.1.1.1.0", "mcafee email gateway")
DETECT_WEB_GATEWAY = v1.contains(".1.3.6.1.2.1.1.1.0", "mcafee web gateway")


class MiscParams(typing.TypedDict, total=True):
    clients: typing.Optional[typing.Tuple[int, int]]
    network_sockets: typing.Optional[typing.Tuple[int, int]]
    time_to_resolve_dns: typing.Optional[typing.Tuple[int, int]]
    time_consumed_by_rule_engine: typing.Optional[typing.Tuple[int, int]]


MISC_DEFAULT_PARAMS = MiscParams(
    clients=None,
    network_sockets=None,
    time_to_resolve_dns=(1500, 2000),
    time_consumed_by_rule_engine=(1500, 2000),
)


@dataclasses.dataclass
class Section:
    """section: mcafee_webgateway_misc"""

    client_count: typing.Optional[int]
    socket_count: typing.Optional[int]
    time_to_resolve_dns: typing.Optional[datetime.timedelta]
    time_consumed_by_rule_engine: typing.Optional[datetime.timedelta]


def _get_param_in_seconds(param: tuple[int, int] | None) -> tuple[float, float] | None:
    """Time is specified in milliseconds.

    >>> _get_param_in_seconds((100, 200))
    (0.1, 0.2)
    """
    if param is None:
        return None
    return param[0] / 1000, param[1] / 1000
