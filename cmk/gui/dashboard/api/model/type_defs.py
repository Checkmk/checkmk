#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Annotated, Final, Literal

from cmk.gui.openapi.framework.model.converter import RegistryConverter, TypedPlainValidator
from cmk.gui.type_defs import InfoName
from cmk.gui.valuespec.definitions import HostStateValue, MonitoringStateValue
from cmk.gui.visuals.info import visual_info_registry
from cmk.livestatus_client import LivestatusColumn


def _validate_info_name(value: str) -> InfoName:
    """Validate that the info name is a valid identifier."""
    RegistryConverter(visual_info_registry).validate(value)
    return InfoName(value)


type AnnotatedInfoName = Annotated[InfoName, TypedPlainValidator(str, _validate_info_name)]


type HostState = Literal["UP", "DOWN", "UNREACHABLE"]
type MonitoringState = Literal["OK", "WARNING", "CRITICAL", "UNKNOWN"]

HOST_STATE_VALUES: Final[Mapping[HostState, HostStateValue]] = {
    "UP": 0,
    "DOWN": 1,
    "UNREACHABLE": 2,
}
MONITORING_STATE_VALUES: Final[Mapping[MonitoringState, MonitoringStateValue]] = {
    "OK": 0,
    "WARNING": 1,
    "CRITICAL": 2,
    "UNKNOWN": 3,
}
_HOST_STATES: Final[Mapping[int, HostState]] = {
    value: state for state, value in HOST_STATE_VALUES.items()
}
_MONITORING_STATES: Final[Mapping[int, MonitoringState]] = {
    value: state for state, value in MONITORING_STATE_VALUES.items()
}


def host_state_of(value: LivestatusColumn) -> HostState:
    """The host state of a livestatus state column."""
    return _HOST_STATES.get(int(str(value)), "UNREACHABLE")


def service_state_of(value: LivestatusColumn) -> MonitoringState:
    """The service state of a livestatus state column."""
    return _MONITORING_STATES.get(int(str(value)), "UNKNOWN")
