#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This module keeps the global state of the ValueStore.
"""

from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import Any, Protocol, TypeVar


class _ValueStoreManagerProtokol(Protocol):
    active_service_interface: MutableMapping[str, Any] | None

    def save(self) -> None:
        ...


_active_host_value_store: _ValueStoreManagerProtokol | None = None


# Caveat: this function (and its docstring) is part of the public Check API.
def get_value_store() -> MutableMapping[str, Any]:
    """Get the value store for the current service from Checkmk

    The returned value store object can be used to persist values
    between different check executions. It is a MutableMapping,
    so it can be used just like a dictionary.
    """
    assert (
        _active_host_value_store is not None
        and _active_host_value_store.active_service_interface is not None
    )
    return _active_host_value_store.active_service_interface


TVSManager = TypeVar("TVSManager", bound=_ValueStoreManagerProtokol)


@contextmanager
def set_value_store_manager(
    vs_manager: TVSManager,
    *,
    store_changes: bool,
) -> Iterator[TVSManager]:
    """Create and load the value store for the host"""
    global _active_host_value_store

    pushed_back_store = _active_host_value_store

    try:
        _active_host_value_store = vs_manager
        yield _active_host_value_store

        if store_changes:
            _active_host_value_store.save()
    finally:
        _active_host_value_store = pushed_back_store
