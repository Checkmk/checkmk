#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any, Literal, TypedDict

__all__ = [
    "PhaseOneResult",
]


class _PiggybackHostsConnectorAttributes(TypedDict):
    hosts: Sequence[str]
    tmpfs_initialization_time: int


class _ExecutionStepAttributes(TypedDict):
    _name: str
    _title: str
    _time_initialized: float
    _time_started: float
    _time_completed: float
    _log_entries: Sequence[str]
    phase: Literal[0, 1, 2]
    status: Literal[0, 1]
    message: str


class _ExecutionStep(TypedDict):
    class_name: Literal["ExecutionStep"]
    attributes: _ExecutionStepAttributes


class _ExecutionStatusAttributes(TypedDict):
    _steps: Sequence[_ExecutionStep]
    _finished: bool
    _time_initialized: float
    _time_completed: float


class _ExecutionStatus(TypedDict):
    class_name: Literal["ExecutionStatus"]
    attributes: _ExecutionStatusAttributes


class _ConnectorObj(TypedDict):
    # Literal["PiggybackHosts"]
    class_name: str  # TODO: replace str type with Literal
    # attributes of new connector objects should be listed here
    attributes: _PiggybackHostsConnectorAttributes | dict[str, Any]


class _PhaseOneAttributes(TypedDict):
    connector_object: _ConnectorObj
    status: _ExecutionStatus


class PhaseOneResult(TypedDict, total=False):
    class_name: Literal["Phase1Result"]
    attributes: _PhaseOneAttributes
