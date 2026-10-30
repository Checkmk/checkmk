#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Entities of the Nutanix v4 API, reduced to the fields the checks read

The v4 agent writes them to the prism_*_v2 sections, the parse functions read them back.
"""

from pydantic import BaseModel, ConfigDict, Field, RootModel


class V4Model(BaseModel):
    model_config = ConfigDict(frozen=True, extra="ignore")

    def to_section(self) -> dict[str, object]:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)


class HostHypervisor(V4Model):
    number_of_vms: int | None = Field(None, alias="numberOfVms")
    acropolis_connection_state: str | None = Field(None, alias="acropolisConnectionState")


class Host(V4Model):
    host_name: str = Field(alias="hostName")
    node_status: str | None = Field(None, alias="nodeStatus")
    memory_size_bytes: int | None = Field(None, alias="memorySizeBytes")
    boot_time_usecs: int | None = Field(None, alias="bootTimeUsecs")
    hypervisor: HostHypervisor = HostHypervisor()


class Hosts(RootModel[list[Host]]):
    model_config = ConfigDict(frozen=True)
