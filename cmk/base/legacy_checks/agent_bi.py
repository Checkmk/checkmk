#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.base.config import special_agent_info

# NOTE: This code is temporarily duplicated from cmk/base/config.py to resolve
# a layering violation.
# This will be resovled with CMK-3812.
# DO NOT USE THIS!!!


class SpecialAgentConfiguration(NamedTuple):
    args: Sequence[str]
    # None makes the stdin of subprocess /dev/null
    stdin: str | None


def agent_bi_arguments(
    params: Sequence[Mapping[str, Any]], hostname: str, ipaddress: str | None
) -> SpecialAgentConfiguration:
    # There is an inconsistency between the WATO rule and the webapi.
    # WATO <-> API
    #  aggr_groups / aggr_group_prefix <-> groups
    #  aggr_name_regex / aggr_name <-> names
    # Note: In 1.6 aggr_name_regex never worked as regex, it always was an exact match
    for param_set in params:
        filter_ = param_set.get("filter", {})
        for replacement, name in (
            ("groups", "aggr_groups"),  # 1.6 (deprecated)
            ("names", "aggr_name_regex"),  # 1.6 (deprecated)
            ("groups", "aggr_group_prefix"),
            ("names", "aggr_name"),
        ):
            if name in filter_:
                filter_[replacement] = filter_.pop(name)

    return SpecialAgentConfiguration([], repr(params))


special_agent_info["bi"] = agent_bi_arguments
