#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from re import Pattern
from typing import Protocol

from omdlib.config_choices import ConfigChoiceHasError

from cmk.ccc.version import Edition

Config = dict[str, str]

ConfigHookChoiceItem = tuple[str, str]
ConfigHookChoices = Pattern[str] | list[ConfigHookChoiceItem] | ConfigChoiceHasError


class _NamedSiteActivation(Protocol):
    def __call__(self, site_name: str, site_home: Path, config: Config) -> None: ...


class _UnusedSiteActivation(Protocol):
    def __call__(self, _site_name: str, site_home: Path, config: Config) -> None: ...


Activation = _NamedSiteActivation | _UnusedSiteActivation


def null_action(_site_name: str, site_home: Path, config: Config) -> None:
    pass


@dataclass(frozen=True)
class PortHook:
    name: str
    display_name: str
    default_port: int
    activation: Activation
    choices: ConfigHookChoices
    depends: Callable[[Config], bool] = lambda _: True


@dataclass(frozen=True)
class Hook:
    name: str
    default: Callable[[Edition], str]
    activation: Activation
    choices: ConfigHookChoices
    depends: Callable[[Config], bool] = lambda _: True
