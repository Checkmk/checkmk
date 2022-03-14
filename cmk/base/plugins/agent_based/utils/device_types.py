#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import enum
import re
from typing import Final, Protocol

from ..agent_based_api.v1 import HostLabel
from ..agent_based_api.v1.type_defs import HostLabelGenerator


class _WithDescription(Protocol):
    @property
    def description(self) -> str:
        ...


def get_device_type_label(section: _WithDescription) -> HostLabelGenerator:
    """Host label function

    Labels:

        cmk/device_type:
            This label is set to values extracted from the device description sent via SNMP.
            Possible values are:
            * appliance
            * fcswitch
            * firewall
            * printer
            * router
            * sensor
            * switch
            * ups
            * wlc

    """
    for device_type in SNMPDeviceType:
        if device_type.name in section.description.upper():
            if device_type is SNMPDeviceType.SWITCH and _is_fibrechannel_switch(
                section.description
            ):
                yield HostLabel("cmk/device_type", "fcswitch")
            else:
                yield HostLabel("cmk/device_type", device_type.name.lower())
            return


# TODO: replace this by HostLabel instances.
class SNMPDeviceType(enum.Enum):
    APPLIANCE = enum.auto()
    FIREWALL = enum.auto()
    PRINTER = enum.auto()
    ROUTER = enum.auto()
    SENSOR = enum.auto()
    SWITCH = enum.auto()
    UPS = enum.auto()
    WLC = enum.auto()


_FIBRECHANNEL_MARKER: Final = {"fc", "fibrechannel", "fibre channel"}


def _is_fibrechannel_switch(description: str) -> bool:
    return any(
        m in description.lower() and not re.search(r"fc\d", description.lower())
        for m in _FIBRECHANNEL_MARKER
    )
