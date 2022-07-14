#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example output from old agent until version 1.2.6
# <<<lnx_quota>>>
# [[[/home]]]
# root      -- 62743228       0       0      0  137561     0     0      0
# proxy     --   288648       0       0      0   14370     0     0      0
# http      --      208       0       0      0      53     0     0      0
# mysql     --  7915856       0       0      0     173     0     0      0

# Example output from new agent since version 1.2.8
# [[[usr:/home]]]
# root      -- 62743228       0       0      0  137561     0     0      0
# proxy     --   288648       0       0      0   14370     0     0      0
# http      --      208       0       0      0      53     0     0      0
# mysql     --  7915856       0       0      0     173     0     0      0
# [[[grp:/home]]]
# root      -- 62743228       0       0      0  137561     0     0      0
# proxy     --   288648       0       0      0   14370     0     0      0
# http      --      208       0       0      0      53     0     0      0
# mysql     --  7915856       0       0      0     173     0     0      0


import time
from typing import Dict, Mapping, Sequence, Tuple

from .agent_based_api.v1 import register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

_SECTION = Mapping[str, Mapping[str, Mapping[str, Sequence[int]]]]

_DEFAULT_PARAMETERS = {"user": True}


def parse(string_table: StringTable) -> _SECTION:
    parsed: Dict = {}
    mode = None
    filesys = None

    for line in string_table:
        if line[0].startswith("[[["):
            # new filesystem detected
            mode, filesys = line[0][3:-3].split(":")

            # new filesystem for quota
            parsed.setdefault(filesys, {})
            parsed[filesys].setdefault(mode, {})

        elif filesys and mode and len(line) == 10:
            # new table entry for quota
            parsed[filesys][mode][line[0]] = [int(x) * 1024 for x in line[2:5]] + [
                int(x) for x in line[5:]
            ]

    return parsed


register.agent_section(
    name="lnx_quota",
    parse_function=parse,
)


def discover(section: _SECTION) -> DiscoveryResult:
    for item, data in section.items():
        yield Service(item=item, parameters={"user": "usr" in data, "group": "grp" in data})


def lnx_quota_limit_check(
    mode: str, what: str, user: str, used: int, soft: int, hard: int, grace: int
) -> Tuple[int, str]:
    def fmt(value: float, what: str) -> str:
        return "%d" % value if what == "files" else render.bytes(value)

    if mode == "usr":
        txt = "User %s" % user
    elif mode == "grp":
        txt = "Group %s" % user

    if used > hard:
        # check, if hard limit is exceeded
        state = 2
        if what == "blocks":
            txt += " exceeded space hard limit %s/%s" % (fmt(used, what), fmt(hard, what))
        elif what == "files":
            txt += " exceeded file hard limit %s/%s" % (fmt(used, what), fmt(hard, what))
    elif soft != 0 and used > soft:
        # check, if soft limit is exceeded
        state = 1
        if what == "blocks":
            txt += " exceeded space soft limit %s/%s" % (fmt(used, what), fmt(soft, what))
        elif what == "files":
            txt += " exceeded file soft limit %s/%s" % (fmt(used, what), fmt(soft, what))

        if grace != 0:
            # check, if grace time is specified
            if grace <= time.time():
                # check, if it was in grace time
                state = 2
                txt += ", grace time exceeded"
            else:
                # check, if it is in grace time
                state = 1
                txt += ", within grace time"
    else:
        state = 0
        txt = ""
    return state, txt


def check(item: str, params: Mapping[str, bool], section: _SECTION) -> CheckResult:
    if not (data := section.get(item)):
        return
    for param_key, mode, name in [("user", "usr", "users"), ("group", "grp", "groups")]:
        if params.get(param_key) is True:
            at_least_one_problematic = False
            for user, values in data[mode].items():
                for what, (used, soft, hard, grace) in [
                    ("blocks", values[:4]),
                    ("files", values[4:]),
                ]:

                    if soft == 0 and hard == 0:
                        continue  # skip entries without limits

                    state, txt = lnx_quota_limit_check(mode, what, user, used, soft, hard, grace)

                    if txt:
                        at_least_one_problematic = True
                    if state != 0 or txt:
                        yield Result(state=State(state), summary=txt)

            if not at_least_one_problematic:
                yield Result(state=State.OK, summary="All %s within quota limits" % name)

    if params.get("user") is False and params.get("group") is False:
        yield Result(state=State.OK, summary="Disabled quota checking")


register.check_plugin(
    name="lnx_quota",
    service_name="Quota: %s",
    check_function=check,
    discovery_function=discover,
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_ruleset_name="lnx_quota",
)
