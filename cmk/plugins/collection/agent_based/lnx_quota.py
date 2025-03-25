#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

import abc
import dataclasses
import enum
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

_DEFAULT_PARAMETERS = {"user": True, "group": False}


class QuotasType(enum.Enum):
    User = "usr"
    Group = "grp"


@dataclasses.dataclass(frozen=True)
class Quota(abc.ABC):
    owner: str
    used: int
    soft: int
    hard: int
    grace: int

    @staticmethod
    @abc.abstractmethod
    def human_readable(v: float) -> str: ...

    @staticmethod
    @abc.abstractmethod
    def exceeded_name() -> str: ...

    def exceeded_no_limit(self) -> str:
        return f"{self.owner} is within quota limits"

    def exceeded_soft_limit(self) -> str:
        return f"{self.owner} exceeded {self.exceeded_name()} soft limit {self.human_readable(self.used)}/{self.human_readable(self.soft)}"

    def exceeded_hard_limit(self) -> str:
        return f"{self.owner} exceeded {self.exceeded_name()} hard limit {self.human_readable(self.used)}/{self.human_readable(self.hard)}"

    def no_limits_set(self) -> str:
        return f"{self.owner} has no {self.exceeded_name()} limits set"


@dataclasses.dataclass(frozen=True)
class BlockQuota(Quota):
    @staticmethod
    def human_readable(v: float) -> str:
        return render.bytes(v)

    @staticmethod
    def exceeded_name() -> str:
        return "space"


@dataclasses.dataclass(frozen=True)
class FileQuota(Quota):
    @staticmethod
    def human_readable(v: float) -> str:
        return "%d" % v

    @staticmethod
    def exceeded_name() -> str:
        return "file"


_Section = Mapping[str, Mapping[QuotasType, Sequence[Quota]]]


def parse(string_table: StringTable) -> _Section:
    parsed: dict = defaultdict(lambda: defaultdict(list))

    mode = None
    filesys_name = None

    for line in string_table:
        if line[0].startswith("[[["):
            # new filesystem detected
            mode, filesys_name = (line[0][3:-3]).split(":")

        elif filesys_name and mode and len(line) == 10:
            # new table entry for quota
            cast_quota = [int(x) * 1024 for x in line[2:5]] + [int(x) for x in line[5:]]
            parsed[filesys_name][QuotasType(mode)].append(BlockQuota(line[0], *cast_quota[:4]))
            parsed[filesys_name][QuotasType(mode)].append(FileQuota(line[0], *cast_quota[4:]))

    return parsed


agent_section_lnx_quota = AgentSection(
    name="lnx_quota",
    parse_function=parse,
)


def discover(section: _Section) -> DiscoveryResult:
    for filesys_name, data in section.items():
        yield Service(
            item=filesys_name,
            parameters={
                "user": (QuotasType.User in data),
                "group": (QuotasType.Group in data),
            },
        )


def lnx_quota_limit_check(quota: Quota, filesys_mode: QuotasType) -> Iterable[Result]:
    if quota.soft == 0 and quota.hard == 0:
        yield Result(state=State.OK, notice=f"{filesys_mode.name} {quota.no_limits_set()}")
        return

    (result,) = check_levels_v1(
        value=quota.used, levels_upper=(quota.soft, quota.hard), notice_only=True
    )
    match result.state:
        case State.OK:
            yield Result(state=State.OK, notice=f"{filesys_mode.name} {quota.exceeded_no_limit()}")
        case State.WARN:
            if quota.soft != 0:
                yield Result(
                    state=State.WARN, summary=f"{filesys_mode.name} {quota.exceeded_soft_limit()}"
                )

                if quota.grace != 0:
                    # check, if grace time is specifieds
                    if quota.grace <= time.time():
                        yield Result(state=State.CRIT, summary="grace time exceeded")
                    else:
                        yield Result(state=State.WARN, summary="within grace time")

        case State.CRIT:
            yield Result(
                state=State.CRIT, summary=f"{filesys_mode.name} {quota.exceeded_hard_limit()}"
            )


def check(item: str, params: Mapping[str, bool], section: _Section) -> CheckResult:
    if not (filesys := section.get(item)):
        return

    if params["user"] is False and params["group"] is False:
        yield Result(state=State.OK, summary="Disabled quota checking")
        return
    for mode, quotas in filesys.items():
        if params[mode.name.lower()] is False:
            continue
        for quota in quotas:
            yield from lnx_quota_limit_check(quota, mode)


check_plugin_lnx_quota = CheckPlugin(
    name="lnx_quota",
    service_name="Quota: %s",
    check_function=check,
    discovery_function=discover,
    check_default_parameters=_DEFAULT_PARAMETERS,
    check_ruleset_name="lnx_quota",
)
