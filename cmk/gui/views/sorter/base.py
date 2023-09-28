#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Mapping, Sequence
from typing import Any, NamedTuple

from cmk.gui.type_defs import ColumnName, ColumnSpec, Row
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
    def vs_parameters(self, painters: Sequence[ColumnSpec]) -> Dictionary:
        """Valuespec to configure optional sorter parameters

        This Dictionary will be visible as sorter specific parameters after selecting this sorter in
        the section "Sorting" in the "Edit View" form.
        """
