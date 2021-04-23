#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
These functions allow checks to keep a memory until the next time
the check is being executed. The most frequent use case is compu-
tation of rates from two succeeding counter values. This is done
via the helper function get_rate(). Averaging is another example
and done by get_average().

While a host is being checked this memory is kept in _cached_item_states.
That is a dictionary. The keys are unique to one check type and
item. The value is free form.

Note: The item state is kept in tmpfs and not reboot-persistant.
Do not store long-time things here. Also do not store complex
structures like log files or stuff.
"""

from contextlib import contextmanager
from typing import Generator, Optional
from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostName

from cmk.base.api.agent_based.type_defs import ValueStore

from ._utils import ValueStoreManager

_active_host_value_store: Optional[ValueStoreManager] = None


def get_value_store() -> ValueStore:
    """Get the value store for the current service from Checkmk

    The returned value store object can be used to persist values
    between different check executions. It is a MutableMapping,
    so it can be used just like a dictionary.
    """
    if _active_host_value_store is None:
        raise MKGeneralException("no value store manager available")
    if _active_host_value_store.active_service_interface is None:
        raise MKGeneralException("no service interface for value store manager available")
    return _active_host_value_store.active_service_interface


@contextmanager
def load_host_value_store(
    host_name: HostName,
    *,
    store_changes: bool,
) -> Generator[ValueStoreManager, None, None]:
    """Select (or create) the correct value store for the host and (re)load it"""
    global _active_host_value_store

    pushed_back_store = _active_host_value_store

    try:

        _active_host_value_store = ValueStoreManager(host_name)
        _active_host_value_store.load()  # TODO incorporate into init

        yield _active_host_value_store

        if store_changes:
            _active_host_value_store.save()
    finally:
        _active_host_value_store = pushed_back_store
