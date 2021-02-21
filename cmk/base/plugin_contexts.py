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
from typing import Optional, Union

from cmk.utils.type_defs import CheckPluginName, CheckPluginNameStr, HostName, ServiceName

from cmk.base.api.agent_based import value_store
import cmk.base.item_state as item_state
from cmk.base.check_utils import Service

# Is set before check/discovery function execution
# Host currently being checked
_hostname: Optional[HostName] = None
_check_type: Optional[CheckPluginNameStr] = None
_service_description: Optional[ServiceName] = None


@contextmanager
def host_context(host_name_: HostName, *, write_state: bool):
    """Make a bit of context information globally available

    So that functions called by checks know this context.
    This is used for both legacy and agent_based API.
    """
    # TODO: this is a mixture of legacy and new Check-API mechanisms. Clean this up!
    try:
        set_hostname(host_name_)
        item_state.load(host_name_)
        yield
    finally:
        reset_hostname()
        if write_state:
            item_state.save(host_name_)
        item_state.cleanup_item_states()


@contextmanager
def service_context(service: Service):
    """Make a bit of context information globally available

    So that functions called by checks know this context.
    set_service is needed for predictive levels!
    This is used for both legacy and agent_based API.
    """
    # TODO: this is a mixture of legacy and new Check-API mechanisms. Clean this up!
    set_service(str(service.check_plugin_name), service.description)
    with value_store.context(service.check_plugin_name, service.item):
        yield


def set_hostname(hostname: Optional[HostName]) -> None:
    """Set the host name for the function host_name that is part of the Check API.
    host_name is used e.g. by the ps-discovery."""
    global _hostname
    _hostname = hostname


def reset_hostname() -> None:
    global _hostname
    _hostname = None


def host_name() -> HostName:
    """Returns the name of the host currently being checked or discovered."""
    if _hostname is None:
        raise RuntimeError("host name has not been set")
    return _hostname


def set_service(
    type_name: Optional[Union[CheckPluginName, str]],
    descr: Optional[ServiceName],
) -> None:
    global _check_type, _service_description
    _check_type = str(type_name)
    _service_description = descr


def check_type() -> CheckPluginNameStr:
    """Returns the name of the check type currently being checked."""
    if _check_type is None:
        raise RuntimeError("check type has not been set")
    return _check_type


def service_description() -> ServiceName:
    """Returns the name of the service currently being checked."""
    if _service_description is None:
        raise RuntimeError("service description has not been set")
    return _service_description
