#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Type

from cmk.utils.plugin_registry import Registry

from cmk.gui.type_defs import ColumnName, SorterFunction


class SorterEntry(NamedTuple):
    sorter: Sorter
    negate: bool
    join_key: Optional[str]


# Is used to add default arguments to the named tuple. Would be nice to have a cleaner solution
SorterEntry.__new__.__defaults__ = (None,) * len(SorterEntry._fields)


class Sorter(abc.ABC):
    """A sorter is used for allowing the user to sort the queried data
    according to a certain logic."""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a sorter. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Used as display string for the sorter in the GUI (e.g. view editor)"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def columns(self) -> Sequence[ColumnName]:
        """Livestatus columns needed for this sorter"""
        raise NotImplementedError()

    @abc.abstractmethod
    def cmp(self, r1: Dict, r2: Dict) -> int:
        """The function cmp does the actual sorting. During sorting it
        will be called with two data rows as arguments and must
        return -1, 0 or 1:

        -1: The first row is smaller than the second (should be output first)
         0: Both rows are equivalent
         1: The first row is greater than the second.

        The rows are dictionaries from column names to values. Each row
        represents one item in the Livestatus table, for example one host,
        one service, etc."""
        raise NotImplementedError()

    @property
    def _args(self) -> Optional[List]:
        """Optional list of arguments for the cmp function"""
        return None

    # TODO: Cleanup this hack
    @property
    def load_inv(self) -> bool:
        """Whether or not to load the HW/SW inventory for this column"""
        return False


class SorterRegistry(Registry[Type[Sorter]]):
    def plugin_name(self, instance: Type[Sorter]) -> str:
        return instance().ident


sorter_registry = SorterRegistry()


# Kept for pre 1.6 compatibility. But also the inventory.py uses this to
# register some painters dynamically
def register_sorter(ident: str, spec: Dict[str, Any]) -> None:
    cls = type(
        "LegacySorter%s" % str(ident).title(),
        (Sorter,),
        {
            "_ident": ident,
            "_spec": spec,
            "ident": property(lambda s: s._ident),
            "title": property(lambda s: s._spec["title"]),
            "columns": property(lambda s: s._spec["columns"]),
            "load_inv": property(lambda s: s._spec.get("load_inv", False)),
            "cmp": spec["cmp"],
        },
    )
    sorter_registry.register(cls)


def declare_simple_sorter(name: str, title: str, column: ColumnName, func: SorterFunction) -> None:
    register_sorter(
        name,
        {"title": title, "columns": [column], "cmp": lambda self, r1, r2: func(column, r1, r2)},
    )
