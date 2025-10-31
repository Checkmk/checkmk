#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypedDict

VSPHERE_OBJECT_NAMES = {"hostsystem": "HostSystem", "virtualmachine": "VM", "template": "Template"}


@dataclass
class VmInfo:
    name: str
    vmtype: str
    hostsystem: str
    state: str

    @property
    def service_name(self) -> str:
        return f"{self.vmtype} {self.name}"


class StateParams(TypedDict):
    standBy: int
    poweredOn: int
    poweredOff: int
    suspended: int
    unknown: int


class ObjectCountParams(TypedDict):
    vm_names: list[str]
    hosts_count: int
    state: int


class ObjectDiscoveryParams(TypedDict):
    templates: bool


ObjectCountParamsMapping = Mapping[Literal["distribution"], list[ObjectCountParams]]
ParsedSection = Mapping[str, VmInfo]
StateParamsMapping = Mapping[Literal["states"], StateParams]
