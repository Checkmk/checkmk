#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.utils.plugin_registry import Registry

from cmk.gui.num_split import cmp_num_split as _cmp_num_split
from cmk.gui.type_defs import ColumnName, PainterSpec, Row, SorterFunction
from cmk.gui.valuespec import Dictionary


class SorterEntry(NamedTuple):
    sorter: Sorter
    negate: bool
    join_key: str | None
    parameters: Mapping[str, Any] | None


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
    def cmp(self, r1: Row, r2: Row, parameters: Mapping[str, Any] | None) -> int:
        """The function cmp does the actual sorting. During sorting it
        will be called with two data rows as arguments and must
        return -1, 0 or 1:

        -1: The first row is smaller than the second (should be output first)
         0: Both rows are equivalent
         1: The first row is greater than the second.

        The rows are dictionaries from column names to values. Each row
        represents one item in the Livestatus table, for example one host,
        one service, etc.

        Only ParameterizedPainters get a Mapping as parameters (A dict produced with the
        Dictionary valuespec returned by `vs_parameters`).
        """
        raise NotImplementedError()

    # TODO: Cleanup this hack
    @property
    def load_inv(self) -> bool:
        """Whether or not to load the HW/SW inventory for this column"""
        return False


class ParameterizedSorter(Sorter):
    @abc.abstractmethod
    def vs_parameters(self, painters: Sequence[PainterSpec]) -> Dictionary:
        """Valuespec to configure optional sorter parameters

        This Dictionary will be visible as sorter specific parameters after selecting this sorter in
        the section "Sorting" in the "Edit View" form.
        """


class SorterRegistry(Registry[type[Sorter]]):
    def plugin_name(self, instance: type[Sorter]) -> str:
        return instance().ident


sorter_registry = SorterRegistry()


# Kept for pre 1.6 compatibility. But also the inventory.py uses this to
# register some painters dynamically
def register_sorter(ident: str, spec: dict[str, Any]) -> None:
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
            "cmp": lambda self, r1, r2, p: spec["cmp"](r1, r2),
        },
    )
    sorter_registry.register(cls)


def declare_simple_sorter(name: str, title: str, column: ColumnName, func: SorterFunction) -> None:
    register_sorter(
        name,
        {"title": title, "columns": [column], "cmp": lambda r1, r2: func(column, r1, r2)},
    )


def cmp_simple_number(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = r1[column]
    v2 = r2[column]
    return (v1 > v2) - (v1 < v2)


def cmp_num_split(column: ColumnName, r1: Row, r2: Row) -> int:
    return _cmp_num_split(r1[column].lower(), r2[column].lower())


def cmp_simple_string(column: ColumnName, r1: Row, r2: Row) -> int:
    v1, v2 = r1.get(column, ""), r2.get(column, "")
    return cmp_insensitive_string(v1, v2)


def cmp_insensitive_string(v1: str, v2: str) -> int:
    c = (v1.lower() > v2.lower()) - (v1.lower() < v2.lower())
    # force a strict order in case of equal spelling but different
    # case!
    if c == 0:
        return (v1 > v2) - (v1 < v2)
    return c


def cmp_string_list(column: ColumnName, r1: Row, r2: Row) -> int:
    v1 = "".join(r1.get(column, []))
    v2 = "".join(r2.get(column, []))
    return cmp_insensitive_string(v1, v2)


def cmp_service_name_equiv(r: str) -> int:
    if r == "Check_MK":
        return -6
    if r == "Check_MK Agent":
        return -5
    if r == "Check_MK Discovery":
        return -4
    if r == "Check_MK inventory":
        return -3  # FIXME: Remove old name one day
    if r == "Check_MK HW/SW Inventory":
        return -2
    return 0


def cmp_custom_variable(r1: Row, r2: Row, key: str, cmp_func: SorterFunction) -> int:
    return (_get_custom_var(r1, key) > _get_custom_var(r2, key)) - (
        _get_custom_var(r1, key) < _get_custom_var(r2, key)
    )


def cmp_ip_address(column: ColumnName, r1: Row, r2: Row) -> int:
    return compare_ips(r1.get(column, ""), r2.get(column, ""))


def compare_ips(ip1: str, ip2: str) -> int:
    def split_ip(ip: str) -> tuple:
        try:
            return tuple(int(part) for part in ip.split("."))
        except ValueError:
            # Make hostnames comparable with IPv4 address representations
            return (255, 255, 255, 255, ip)

    v1, v2 = split_ip(ip1), split_ip(ip2)
    return (v1 > v2) - (v1 < v2)


def _get_custom_var(row: Row, key: str) -> str:
    return row["custom_variables"].get(key, "")
