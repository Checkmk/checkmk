#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import enum
from contextlib import suppress
from typing import Any, Dict, Final, NewType, TypedDict, Union
from urllib.parse import quote_plus, unquote_plus

from ._misc import HostName

__all__ = [
    "get_bakery_target",
    "AgentConfig",
    "AgentHash",
    "AgentPackagePlatform",
    "BakeryOpSys",
    "BakeryTargetVanilla",
    "BakeryTargetFolder",
    "BakeryTargetHost",
    "BakeryTarget",
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


class BakeryTargetVanilla:
    # Be aware:
    # At the time of this writing, agents will not be baked if this does not start with '_'
    _SERIALIZED = "_VANILLA"

    def serialize(self) -> str:
        """Return a string that is also suitable as file name"""
        return self._SERIALIZED

    @classmethod
    def deserialize(cls, raw: str) -> BakeryTargetVanilla:
        if raw != cls._SERIALIZED:
            raise ValueError(raw)
        return cls()

    def __hash__(self) -> int:
        return hash(self.serialize())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __eq__(self, other: object) -> bool:
        return type(self) is type(other)


class BakeryTargetFolder:

    # Be aware:
    # At the time of this writing, agents will not be baked if this does not start with '_'
    _PRE = "_GENERIC["
    _SUF = "]"

    def __init__(self, path_for_rule_matching: str) -> None:
        self.folder: Final = path_for_rule_matching

    def serialize(self) -> str:
        """Return a string that is also suitable as file name

        We are mainly concerned with escaping '/'.
        urllibs `quote_plus` is a nice trade-off between safety and readability.
        """
        return f"{self._PRE}{quote_plus(self.folder)}{self._SUF}"

    @classmethod
    def deserialize(cls, raw: str) -> BakeryTargetFolder:
        if not raw.startswith(cls._PRE) or not raw.endswith(cls._SUF):
            raise ValueError(raw)
        folder_str = raw[len(cls._PRE) : -len(cls._SUF)]
        return cls(unquote_plus(folder_str))

    def __hash__(self) -> int:
        return hash(self.serialize())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.folder!r})"

    def __eq__(self, other: object) -> bool:
        return (
            type(self) is type(other) and self.folder == other.folder  # type: ignore[attr-defined]
        )


class BakeryTargetHost:
    def __init__(self, host_name: HostName) -> None:
        self.host_name: Final = host_name

    def serialize(self) -> str:
        return str(self.host_name)

    @classmethod
    def deserialize(cls, raw: str) -> BakeryTargetHost:
        return cls(HostName(raw))

    def __hash__(self) -> int:
        return hash(self.serialize())

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.host_name!r})"

    def __eq__(self, other: object) -> bool:
        return (
            type(self) is type(other)
            and self.host_name == other.host_name  # type: ignore[attr-defined]
        )


# Type for entries in data structures that may contain any of the above types.
BakeryTarget = Union[BakeryTargetVanilla, BakeryTargetFolder, BakeryTargetHost]


def get_bakery_target(raw: str) -> BakeryTarget:
    with suppress(ValueError):
        return BakeryTargetVanilla.deserialize(raw)

    with suppress(ValueError):
        return BakeryTargetFolder.deserialize(raw)

    return BakeryTargetHost(HostName(raw))


class BakerySigningCredentials(TypedDict):
    certificate: str
    private_key: str
