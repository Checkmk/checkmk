#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from . import metric

__all__ = [
    "PassiveCheck",
    "ActiveCheck",
    "HostCheckCommand",
    "NagiosPlugin",
    "Renaming",
    "Scaling",
    "RenamingAndScaling",
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
class Renaming:
    rename_to: metric.Name


@dataclass(frozen=True)
class Scaling:
    scale_by: int | float

    def __post_init__(self) -> None:
        assert self.scale_by


@dataclass(frozen=True)
class RenamingAndScaling:
    rename_to: metric.Name
    scale_by: int | float

    def __post_init__(self) -> None:
        assert self.scale_by


@dataclass(frozen=True)
class Translation:
    name: str
    check_commands: Sequence[PassiveCheck | ActiveCheck | HostCheckCommand | NagiosPlugin]
    translations: Mapping[metric.Name, Renaming | Scaling | RenamingAndScaling]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError(self.name)
        assert self.check_commands and self.translations
