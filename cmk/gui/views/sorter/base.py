#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, NamedTuple, Protocol

from cmk.gui.config import Config
from cmk.gui.http import Request
from cmk.gui.type_defs import ColumnName, ColumnSpec, Row
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.valuespec import Dictionary


class SorterProtocol(Protocol):
    def __call__(
        self,
        r1: Row,
        r2: Row,
        *,
        parameters: Mapping[str, Any] | None,
        config: Config,
        request: Request,
    ) -> int:
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


class SorterEntry(NamedTuple):
    sorter: Sorter
    negate: bool
    join_key: str | None
    parameters: Mapping[str, Any] | None


class Sorter:
    """A sorter is used to sort the queried view rows according to a certain logic."""

    def __init__(
        self,
        ident: str,
        title: str | LazyString,
        columns: Sequence[ColumnName],
        sort_function: SorterProtocol,
        load_inv: bool = False,
    ):
        self.ident = ident
        self._title = title
        self.columns = columns
        self.cmp = sort_function
        self.load_inv = load_inv

    @property
    def title(self) -> str:
        return str(self._title)


class ParameterizedSorter(Sorter):
    def __init__(
        self,
        ident: str,
        title: str | LazyString,
        columns: Sequence[ColumnName],
        sort_function: SorterProtocol,
        parameter_valuespec: Callable[[Config, Sequence[ColumnSpec]], Dictionary],
        load_inv: bool = False,
    ):
        super().__init__(ident, title, columns, sort_function, load_inv)
        self.vs_parameters = parameter_valuespec
