#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import enum
from typing import Any, Dict, Literal, NewType, TypedDict, Union

__all__ = [
    "AgentConfig",
    "AgentHash",
    "AgentPackagePlatform",
    "BakeryOpSys",
    "BuiltinBakeryHostName",
    "OrdinaryBakeryHostName",
    "BakeryHostName",
    "BakerySigningCredentials",
]

AgentHash = NewType("AgentHash", str)
AgentConfig = Dict[str, Any]  # TODO Split into more sub configs


class AgentPackagePlatform(enum.Enum):
    LINUX_DEB = "linux_deb"
    LINUX_RPM = "linux_rpm"
    SOLARIS_PKG = "solaris_pkg"
    WINDOWS_MSI = "windows_msi"
    LINUX_TGZ = "linux_tgz"
    SOLARIS_TGZ = "solaris_tgz"
    AIX_TGZ = "aix_tgz"

    def __str__(self) -> str:
        return str(self.value)


# TODO(au): Replace usage with AgentPackagePlatform
# But we need complete typing in cmk.gui.cee.agent_bakery first before we can safely do this.
BakeryOpSys = NewType("BakeryOpSys", str)


class BuiltinBakeryHostName(enum.Enum):
    """Type for representation of the special agent types
    VANILLA and GENERIC. Yields the same interface as OrdinaryBakeryHostName
    in order to enable a generic handling in one data structure.
    """

    def __init__(self, raw_name: str, name: str) -> None:
        self.raw_name = raw_name
        self._display_name = name

    def __str__(self) -> str:
        return self._display_name

    VANILLA = ("_VANILLA", "VANILLA")
    GENERIC = ("_GENERIC", "GENERIC")


class OrdinaryBakeryHostName(str):
    """Wrapper for normal HostNames, when used as a mapping to an agent,
    that enables a generic handling alongside the special agent types
    VANILLA and GENERIC.
    """

    @property
    def raw_name(self) -> str:
        return self


# Type for entries in data structures that contain both of the above types.
BakeryHostName = Union[
    Literal[BuiltinBakeryHostName.VANILLA, BuiltinBakeryHostName.GENERIC], OrdinaryBakeryHostName
]


class BakerySigningCredentials(TypedDict):
    certificate: str
    private_key: str
