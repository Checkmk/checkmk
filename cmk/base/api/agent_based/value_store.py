#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Implements a first shot at the "value_store". Quite literally only an AP*I*
"""
from typing import Any, Iterator, Optional
from contextlib import contextmanager

from cmk.utils.exceptions import MKGeneralException
from cmk.utils.type_defs import CheckPluginName

from cmk.base.api.agent_based.type_defs import ValueStore

# TODO: this API violiation is due to the fact that this value_store
# is currently nothing more than a polished version of item state.
from cmk.base.item_state import (  # pylint: disable=cmk-module-layer-violation
    set_item_state,  # for __setitem__
    clear_item_state,  # for __delitem__
    get_all_item_states,  # for __len__, __iter__
    get_item_state_prefix,  # for __repr__, context
    set_item_state_prefix,  # for context
)


class _ValueStore(ValueStore):
    """_ValueStore objects are used to persist values across check intervals"""
    @staticmethod
    def _raise_for_scope_violation():
        if not get_item_state_prefix():
            raise MKGeneralException("accessing value store outside check function")

    def __getitem__(self, key: str) -> Any:
        self._raise_for_scope_violation()
        unique_key = get_item_state_prefix() + (key,)
        return get_all_item_states()[unique_key]

    def __setitem__(self, key: str, value: Any) -> None:
        self._raise_for_scope_violation()
        if not isinstance(key, str):
            raise TypeError("key must be str")
        return set_item_state(key, value)

    def __delitem__(self, key: str) -> None:
        self._raise_for_scope_violation()
        unique_key = get_item_state_prefix() + (key,)
        if unique_key not in get_all_item_states():
            raise KeyError(key)
        clear_item_state(key)

    def __len__(self) -> int:
        self._raise_for_scope_violation()
        prefix = get_item_state_prefix()
        return sum(unique_key[:2] == prefix for unique_key in get_all_item_states())

    def __iter__(self) -> Iterator:
        self._raise_for_scope_violation()
        prefix = get_item_state_prefix()
        return iter(
            unique_key[-1] for unique_key in get_all_item_states() if unique_key[:2] == prefix)

    @staticmethod
    def __repr__() -> str:
        return "<value store %r>" % (get_item_state_prefix(),)


_value_store = _ValueStore()


def get_value_store() -> ValueStore:
    """Get the value store for the current service from Checkmk

    The returned value store object can be used to persist values
    between different check executions. It is a MutableMapping,
    so it can be used just like a dictionary.
    """
    # At the moment this seems not really necessary. But it gives us options
    # for future changes: We can put code here, that will only be executed
    # if the plugin actually needs the value_store, e.g. lazy file loading.
    return _value_store


@contextmanager
def context(plugin_name: CheckPluginName, item: Optional[str]) -> Iterator[None]:
    """Set item state prefix"""
    saved_prefix = get_item_state_prefix()
    set_item_state_prefix(str(plugin_name), item)

    try:
        yield
    finally:
        set_item_state_prefix(*saved_prefix)
