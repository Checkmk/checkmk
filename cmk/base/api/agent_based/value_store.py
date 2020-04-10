#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Implements a first shot at the "value_store". Quite literally only an AP*I*
"""
from typing import Any, Iterator  # pylint: disable=unused-import
import collections
from cmk.base.item_state import (
    set_item_state,  # for __setitem__
    get_item_state,  # for __getitem__
    clear_item_state,  # for __delitem__
    get_all_item_states,  # for __len__, __iter__
    get_item_state_prefix,  # for __repr__
)


class _ValueStore(collections.abc.MutableMapping):
    """_ValueStore objects are used to persist values across check intervals"""
    def __getitem__(self, key):
        # type: (str) -> Any
        if key not in self:
            raise KeyError(key)
        return get_item_state(key)

    @staticmethod
    def __setitem__(key, value):
        # type: (str, Any) -> None
        if not isinstance(key, str):
            raise TypeError("key must be str")
        return set_item_state(key, value)

    def __delitem__(self, key):
        # type: (str) -> None
        if key not in self:
            raise KeyError(key)
        clear_item_state(key)
        return self.__setitem__(key, None)

    @staticmethod
    def __len__():
        # type: () -> int
        return len(get_all_item_states())

    @staticmethod
    def __iter__():
        # type: () -> Iterator
        return iter(unique_key[-1] for unique_key in get_all_item_states())

    @staticmethod
    def __repr__():
        # type: () -> str
        return "<value store %r>" % (get_item_state_prefix(),)


value_store = _ValueStore()
