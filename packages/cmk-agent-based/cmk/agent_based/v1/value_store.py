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

This package exposes one function to the plugins (via the API), and
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


.. autoclass:: TypeValueStoreManager

"""


from collections.abc import Iterator, MutableMapping
from contextlib import contextmanager
from typing import Any, Protocol, TypeVar


class _ValueStoreManagerProtokol(Protocol):
    @property
    def active_service_interface(self) -> MutableMapping[str, Any] | None:  # type: ignore[misc]
        ...

    def save(self) -> None:
        ...


_active_host_value_store: _ValueStoreManagerProtokol | None = None


# Caveat: this function (and its docstring) is part of the public Check API.
def get_value_store() -> MutableMapping[str, Any]:  # type: ignore[misc]
    """Get the value store for the current service from Checkmk

    The returned value store object can be used to persist values
    between different check executions. It is a MutableMapping,
    so it can be used just like a dictionary.
    """
    assert (
        _active_host_value_store is not None
        and _active_host_value_store.active_service_interface is not None  # type: ignore[misc]
    )
    return _active_host_value_store.active_service_interface  # type: ignore[misc]


TypeValueStoreManager = TypeVar("TypeValueStoreManager", bound=_ValueStoreManagerProtokol)


@contextmanager
def set_value_store_manager(
    vs_manager: TypeValueStoreManager,
    *,
    store_changes: bool,
) -> Iterator[TypeValueStoreManager]:
    """Create and load the value store for the host

    THIS FUNCTION IS NOT TO BE USED BY PLUGINS, AND NOT PART OF THE PLUGIN API.
    """
    # ^- and yet it sits in this package. That's what you get for using a global state.
    global _active_host_value_store  # pylint: disable=global-statement

    pushed_back_store = _active_host_value_store

    try:
        _active_host_value_store = vs_manager
        yield _active_host_value_store

        if store_changes:
            _active_host_value_store.save()
    finally:
        _active_host_value_store = pushed_back_store
