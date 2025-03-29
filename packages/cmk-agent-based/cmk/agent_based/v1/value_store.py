#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
This package allows checks to keep a memory until the next time
the check is being executed.

The most frequent use case is computation of rates from two succeeding counter values.

While a host is being checked this memory is kept in this module.

.. NOTE::

  The value stores file is kept in tmpfs and may not be reboot-persistent.
  Do not store long-time things here. Also do not store complex
  structures like log files or stuff.

This package exposes one function to the plug-ins (via the API), and
one function to the backend.

Check API
---------

.. autofunction:: get_value_store


Backend
-------

It is the backends responsibility to load the appropriate
host value store and enter the services context, before
the check function is called.


.. autofunction:: set_value_store_manager

.. autoclass:: _TypeValueStoreManager

.. autoclass:: _ValueStoreManagerProtocol

"""

from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import Any, Protocol, TypeVar


class _ValueStoreManagerProtocol(Protocol):
    @property
    def active_service_interface(self) -> MutableMapping[str, object] | None: ...

    def save(self) -> None: ...


_active_host_value_store: _ValueStoreManagerProtocol | None = None


def get_value_store() -> MutableMapping[str, Any]:  # type: ignore[explicit-any]
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


_TypeValueStoreManager = TypeVar("_TypeValueStoreManager", bound=_ValueStoreManagerProtocol)


@contextmanager
def set_value_store_manager(
    vs_manager: _TypeValueStoreManager,
    *,
    store_changes: bool,
) -> Iterator[_TypeValueStoreManager]:
    """Create and load the value store for the host

    This class is not to be used by plug-ins, and not part of the plug-in API.
    """
    # ^- and yet it sits in this package. That's what you get for using a global state.
    global _active_host_value_store

    pushed_back_store = _active_host_value_store

    try:
        _active_host_value_store = vs_manager
        yield _active_host_value_store

        if store_changes:
            _active_host_value_store.save()
    finally:
        _active_host_value_store = pushed_back_store
