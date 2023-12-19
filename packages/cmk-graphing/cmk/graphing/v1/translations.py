#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

__all__ = [
    "PassiveCheck",
    "ActiveCheck",
    "HostCheckCommand",
    "NagiosPlugin",
    "RenameTo",
    "ScaleBy",
    "RenameToAndScaleBy",
]


@dataclass(frozen=True)
class PassiveCheck:
    # prefix: check_mk-
    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class ActiveCheck:
    # prefix: check_mk_active-
    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class HostCheckCommand:
    # prefix: check-mk-
    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class NagiosPlugin:
    # prefix: check_
    name: str

    def __post_init__(self) -> None:
        assert self.name


@dataclass(frozen=True)
class RenameTo:
    rename_to: str

    def __post_init__(self) -> None:
        if not self.rename_to:
            raise ValueError(self.rename_to)


@dataclass(frozen=True)
class ScaleBy:
    scale_by: int | float

    def __post_init__(self) -> None:
        assert self.scale_by


@dataclass(frozen=True)
class RenameToAndScaleBy:
    rename_to: str
    scale_by: int | float

    def __post_init__(self) -> None:
        if not self.rename_to:
            raise ValueError(self.rename_to)
        assert self.scale_by


@dataclass(frozen=True, kw_only=True)
class Translation:
    name: str
    check_commands: Sequence[PassiveCheck | ActiveCheck | HostCheckCommand | NagiosPlugin]
    translations: Mapping[str, RenameTo | ScaleBy | RenameToAndScaleBy]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.check_commands and self.translations
        for name in self.translations:
            if isinstance(name, str) and not name:
                raise ValueError(self.name)
