#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from ._utils import HostConfig, HTTPProxy, Secret

_ParsedParameters = TypeVar("_ParsedParameters")


@dataclass(frozen=True)
class SpecialAgentCommand:
    command_arguments: Sequence[str | Secret]
    stdin: str | None = None


@dataclass(frozen=True)
class SpecialAgentConfig(Generic[_ParsedParameters]):
    name: str
    parameter_parser: Callable[[Mapping[str, object]], _ParsedParameters]
    commands_function: Callable[
        [_ParsedParameters, HostConfig, Mapping[str, HTTPProxy]], Iterable[SpecialAgentCommand]
    ]
