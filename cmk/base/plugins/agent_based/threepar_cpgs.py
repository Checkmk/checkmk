#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pydantic

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

from .agent_based_api.v1 import register
from .utils.threepar import parse_3par


class SpaceUsage(pydantic.BaseModel):
    totalMiB: int
    usedMiB: int

    @property
    def freeMiB(self):
        return self.totalMiB - self.usedMiB


class ThreeparCPG(pydantic.BaseModel):
    name: str
    state: int
    num_fpvvs: int = pydantic.Field(alias="numFPVVs")  # number of Fully Provisioned Virtual Volumes
    num_tdvvs: int = pydantic.Field(alias="numTDVVs")  # number of Thinly Deduped Virtual Volumes
    num_tpvvs: int = pydantic.Field(
        alias="numTPVVs"
    )  # number of Thinly Provisioned Virtual Volumes
    sa_usage: SpaceUsage = pydantic.Field(alias="SAUsage")  # Snapshot administration usage
    sd_usage: SpaceUsage = pydantic.Field(alias="SDUsage")  # Snapshot data space usage
    usr_usage: SpaceUsage = pydantic.Field(alias="UsrUsage")  # User data space usage


ThreeparCPGSection = Mapping[str, ThreeparCPG]


def parse_threepar_cpgs(string_table: StringTable) -> ThreeparCPGSection:
    if (raw_members := parse_3par(string_table).get("members")) is None:
        return {}

    return {cpgs.get("name"): ThreeparCPG.parse_obj(cpgs) for cpgs in raw_members}


def count_threepar_vvs(cpg: ThreeparCPG) -> int:
    return cpg.num_fpvvs + cpg.num_tdvvs + cpg.num_tpvvs


register.agent_section(
    name="3par_cpgs",
    parse_function=parse_threepar_cpgs,
)
