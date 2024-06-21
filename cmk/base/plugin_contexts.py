#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Implents the magical host_name, check_type and service_description functions.

This is aweful, but we can not get rid of it, as this is currently needed by
(at least)
 * logwatch
 * robotmk
 * legacy check_* agent_* files ("argument thingys", supported last in 2.3)
"""

from collections.abc import Iterator
from contextlib import contextmanager

# Is set before check/discovery function execution
# Host currently being checked

# **Types must remain string, they're passed to API clients!**
_hostname: str | None = None
_check_type: str | None = None
_service_description: str | None = None


@contextmanager
def current_host(
    host_name_: str,  # do not make this `HostName`.
) -> Iterator[None]:
    """Make a bit of context information globally available

    So that functions called by checks know this context.
    This is used for both legacy and agent_based API.
    """
    # The host name must at least (!) be set for
    # * the host_name() calls commonly used in the legacy checks
    # * predictive levels
    global _hostname
    # we do not encourage nested contexts at all -- but it should work.
    previous_host_name = _hostname
    _hostname = host_name_
    try:
        yield
    finally:
        _hostname = previous_host_name


@contextmanager
def current_service(
    plugin_name: str,  # do not make this `CheckPluginName`
    description: str,  # do not make this `ServiceDescription`
) -> Iterator[None]:  # do bot
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


def host_name() -> str:
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
        raise RuntimeError("service name has not been set")
    return _service_description
