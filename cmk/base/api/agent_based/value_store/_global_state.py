#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module keeps the global state of the ValueStore.
"""

from collections.abc import Generator, MutableMapping
from contextlib import contextmanager
from typing import Any

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import HostName

from ._utils import ValueStoreManager

_active_host_value_store: ValueStoreManager | None = None


# Caveat: this function (and its docstring) is part of the public Check API.
def get_value_store() -> MutableMapping[str, Any]:
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
    """Create and load the value store for the host"""
    global _active_host_value_store

    pushed_back_store = _active_host_value_store

    try:
        _active_host_value_store = ValueStoreManager(host_name)
        yield _active_host_value_store

        if store_changes:
            _active_host_value_store.save()
    finally:
        _active_host_value_store = pushed_back_store
