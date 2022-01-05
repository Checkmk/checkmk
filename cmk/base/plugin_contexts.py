#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# NOTE: This module is for dependency-breaking purposes only, and its contents
# should probably moved somewhere else when there are no import cycles anymore.
# But at the current state of affairs we have no choice, otherwise an
# incremental cleanup is impossible.
from contextlib import contextmanager
from typing import Optional

from cmk.utils.type_defs import CheckPluginName, HostName, ServiceName

# Is set before check/discovery function execution
# Host currently being checked
# Types must remain string, they're passed to API clients!
_hostname: Optional[HostName] = None
_check_type: Optional[str] = None
_service_description: Optional[str] = None


@contextmanager
def current_host(host_name_: HostName):
    """Make a bit of context information globally available

    So that functions called by checks know this context.
    This is used for both legacy and agent_based API.
    """
    global _hostname
    # we do not encourage nested contexts at all -- but it should work.
    previous_host_name = _hostname
    _hostname = host_name_
    try:
        yield
    finally:
        _hostname = previous_host_name


@contextmanager
def current_service(plugin_name: CheckPluginName, description: ServiceName):
    """Make a bit of context information globally available

    So that functions called by checks know this context.
    set_service is needed for predictive levels!
    This is used for both legacy and agent_based API.
    """
    global _check_type, _service_description
    previous_check_type = _check_type
    previous_service_description = _service_description

    try:
        _check_type = str(plugin_name)
        _service_description = str(description)
        yield
    finally:
        _check_type = previous_check_type
        _service_description = previous_service_description


def host_name() -> HostName:
    """Returns the name of the host currently being checked or discovered."""
    if _hostname is None:
        raise RuntimeError("host name has not been set")
    return _hostname


def check_type() -> str:
    """Returns the name of the check type currently being checked."""
    if _check_type is None:
        raise RuntimeError("check type has not been set")
    return _check_type


def service_description() -> str:
    """Returns the name of the service currently being checked."""
    if _service_description is None:
        raise RuntimeError("service description has not been set")
    return _service_description
