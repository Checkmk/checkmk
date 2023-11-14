#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TypeAlias


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


CheckCommandType: TypeAlias = PassiveCheck | ActiveCheck | HostCheckCommand | NagiosPlugin


@dataclass(frozen=True)
class Renaming:
    rename_to: str

    def __post_init__(self) -> None:
        assert self.rename_to


@dataclass(frozen=True)
class Scaling:
    scale_by: int | float

    def __post_init__(self) -> None:
        assert self.scale_by


@dataclass(frozen=True)
class RenamingAndScaling:
    rename_to: str
    scale_by: int | float

    def __post_init__(self) -> None:
        assert self.rename_to
        assert self.scale_by


TranslationType: TypeAlias = Renaming | Scaling | RenamingAndScaling


@dataclass(frozen=True)
class Translations:
    name: str
    check_commands: Sequence[CheckCommandType]
    translations: Mapping[str, TranslationType]

    def __post_init__(self) -> None:
        assert self.name and self.check_commands and self.translations
