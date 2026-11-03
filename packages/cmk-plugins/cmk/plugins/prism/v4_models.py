#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Entities of the Nutanix v4 API, reduced to the fields the checks read

The v4 agent writes them to the prism_*_v2 sections, the parse functions read them back.
"""

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, RootModel


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


class AlertParameterValue(V4Model):
    string_value: str | None = Field(None, alias="stringValue")
    int_value: int | None = Field(None, alias="intValue")

    def as_text(self) -> str | None:
        if self.string_value is not None:
            return self.string_value
        return None if self.int_value is None else str(self.int_value)


class AlertParameter(V4Model):
    param_name: str | None = Field(None, alias="paramName")
    param_value: AlertParameterValue = Field(AlertParameterValue(), alias="paramValue")


class AlertSource(V4Model):
    type: str | None = None


class Alert(V4Model):
    severity: str
    message: str
    creation_time: AwareDatetime = Field(alias="creationTime")
    parameters: list[AlertParameter] = []
    source_entity: AlertSource | None = Field(None, alias="sourceEntity")


class Alerts(RootModel[list[Alert]]):
    model_config = ConfigDict(frozen=True)
