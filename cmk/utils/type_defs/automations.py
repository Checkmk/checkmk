#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Literal, Sequence, TypedDict, Union


class PiggybackHostsConnectorAttributes(TypedDict):
    hosts: Sequence[str]
    tmpfs_initialization_time: int


class ExecutionStepAttributes(TypedDict):
    _name: str
    _title: str
    _time_initialized: float
    _time_started: float
    _time_completed: float
    _log_entries: Sequence[str]
    phase: Literal[0, 1, 2]
    status: Literal[0, 1]
    message: str


class ExecutionStep(TypedDict):
    class_name: Literal["ExecutionStep"]
    attributes: ExecutionStepAttributes


class ExecutionStatusAttributes(TypedDict):
    _steps: Sequence[ExecutionStep]
    _finished: bool
    _time_initialized: float
    _time_completed: float


class ExecutionStatus(TypedDict):
    class_name: Literal["ExecutionStatus"]
    attributes: ExecutionStatusAttributes


class ConnectorObj(TypedDict):
    # Literal["PiggybackHosts"]
    class_name: str  # TODO: replace str type with Literal
    # attributes of new connector objects should be listed here
    attributes: Union[PiggybackHostsConnectorAttributes, dict]


class PhaseOneAttributes(TypedDict):
    connector_object: ConnectorObj
    status: ExecutionStatus


class PhaseOneResult(TypedDict, total=False):
    class_name: Literal["Phase1Result"]
    attributes: PhaseOneAttributes
