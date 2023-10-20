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
class ActiveCheckCommand:
    """
    Definition to create an active service

    Args:
        service_description: Description with which the active service is created
        command_arguments: Arguments to run the active check with
    """

    service_description: str
    command_arguments: Sequence[str | Secret]


@dataclass(frozen=True)
class ActiveCheckConfig(Generic[_ParsedParameters]):
    name: str
    parameter_parser: Callable[[Mapping[str, object]], _ParsedParameters]
    commands_function: Callable[
        [_ParsedParameters, HostConfig, Mapping[str, HTTPProxy]], Iterable[ActiveCheckCommand]
    ]
