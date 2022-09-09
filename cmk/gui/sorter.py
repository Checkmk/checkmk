#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Sequence, Type, TYPE_CHECKING

from cmk.utils.plugin_registry import Registry

from cmk.gui.type_defs import ColumnName, SorterFunction
from cmk.gui.valuespec import ValueSpec

if TYPE_CHECKING:
    from cmk.gui.plugins.views.utils import Cell


class SorterEntry(NamedTuple):
    sorter: Sorter
    negate: bool
    join_key: Optional[str]


# Is used to add default arguments to the named tuple. Would be nice to have a cleaner solution
SorterEntry.__new__.__defaults__ = (None,) * len(SorterEntry._fields)  # type: ignore[attr-defined]


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


class DerivedColumnsSorter(Sorter):
    # TODO(ml): This really looks wrong.  `derived_columns` is most certainly
    #           on the wrong class (it should be on `Cell` or `Painter`, just
    #           look at the few places it is implemented) and without this new
    #           method, this class is just a regular `Sorter`.  We should get
    #           rid of this useless piece of code.
    """
    Can be used to transfer an additional parameter to the Sorter instance.

    To transport the additional parameter through the url and other places the
    parameter is added to the sorter name seperated by a colon.

    This mechanism is used by the Columns "Service: Metric History", "Service:
    Metric Forecast": Those columns can be sorted by "Sorting"-section in
    the "Edit View" only after you added the column to the columns list and
    saved the view, or by clicking on the column header in the view.

    It's also used by host custom attributes: Those can be sorted by the
    "Sorting"-section in the "Edit View" options independent of the column
    section.
    """

    # TODO: should somehow be harmonized. this is probably not possible as the
    # metric sorting options can not be serialized into a short/simple string,
    # this is why the uuid option was introduced. Now there are basically three
    # different ways to subselect sorting options:
    # * don't use subselect at all (see Inventory): simply put all the posible
    #   values with a prefix into the sorting list (drawback: long list)
    # * don't use explicit options for sorting (see Metrics): link between
    #   columns and sorting via uuid (drawback: have to display column to
    #   activate sorting)
    # * use explicit options for sorting (see Custom Attributes): Encode the
    #   choosen value in the name (possible because it's only a simple string
    #   instead of complex options as with the metrics) and append it to the
    #   name of the column (drawback: it's the third hack)

    @abc.abstractmethod
    def derived_columns(self, cells: Iterable["Cell"], uuid: Optional[str]) -> None:
        # TODO: rename uuid, as this is no longer restricted to uuids
        raise NotImplementedError()

    def get_parameters(self) -> Optional[ValueSpec]:
        """
        If not None, this ValueSpec will be visible after selecting this Sorter
        in the section "Sorting" in the "Edit View" form
        """
        return None


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
