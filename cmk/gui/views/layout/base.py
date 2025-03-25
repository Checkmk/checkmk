#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from collections.abc import Sequence

from cmk.gui.painter.v0 import Cell
from cmk.gui.type_defs import Rows, ViewSpec


class Layout(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a layout. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """Short human readable title of the layout"""
        raise NotImplementedError()

    @abc.abstractmethod
    def render(
        self,
        rows: Rows,
        view: ViewSpec,
        group_cells: Sequence[Cell],
        cells: Sequence[Cell],
        num_columns: int,
        show_checkboxes: bool,
    ) -> None:
        """Render the given data in this layout"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def can_display_checkboxes(self) -> bool:
        """Whether this layout can display checkboxes for selecting rows"""
        raise NotImplementedError()

    @property
    def painter_options(self) -> list[str]:
        """Returns the painter option identities used by this layout"""
        return []

    @property
    def has_individual_csv_export(self) -> bool:
        """Whether this layout has an individual CSV export implementation"""
        return False

    @property
    def hide_entries_per_row(self) -> bool:
        """Whether this layout has displays the entries per row option"""
        return False

    def csv_export(
        self, rows: Rows, view: ViewSpec, group_cells: Sequence[Cell], cells: Sequence[Cell]
    ) -> None:
        """Render the given data using this layout for CSV"""
