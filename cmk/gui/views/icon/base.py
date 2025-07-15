#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Literal

from cmk.gui.type_defs import ColumnName, Row
from cmk.gui.type_defs import Icon as IconSpec
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.utils.tags import TagID


class Icon:
    def __init__(
        self,
        *,
        ident: str,
        title: str | LazyString,
        render: Callable[
            [
                Literal["host", "service"],
                Row,
                Sequence[TagID],
                Mapping[str, str],
            ],
            None
            | IconSpec
            | HTML
            | tuple[IconSpec, str]
            | tuple[IconSpec, str, str]
            | tuple[IconSpec, str, str | None]
            | tuple[IconSpec, str, tuple[str, str]],
        ],
        columns: Sequence[ColumnName] = (),
        host_columns: Sequence[ColumnName] = (),
        service_columns: Sequence[ColumnName] = (),
        type_: str = "icon",
        sort_index: int = 30,
        toplevel: bool = False,
    ) -> None:
        """
        Args:
            ident: Unique identifier for this icon. This is used in the
                configuration to enable or disable the icon.
            title: Display title to represent the icon in lists in the UI.
            columns: List of livestatus columns needed by this icon
                idependent of the queried table. The table prefix will be
                added to each column (e.g. name -> host_name)
            host_columns: List of livestatus columns needed by this icon
                when it is displayed for a host row. The prefix host_ will
                be added to each column (e.g. name -> host_name)
            service_columns: List of livestatus columns needed by this icon
                when it is displayed for a service row. The prefix host_ will
                be added to each column (e.g. description -> service_description)
            render_func: A function that renders the icon.
            type_: The type of the icon. This is either "icon" or
                "custom_icon".
            sort_index: The sort index of the icon. Icons are sorted
                ascending by this value.
            toplevel: Whether the icon is displayed in the view or in the action menu.

        """
        self.ident = ident
        self._title = title
        self.type = type_  # Literal["icon", "custom_icon"]
        self._sort_index = sort_index
        self._toplevel = toplevel
        self._render_func = render
        self.columns = columns
        self.host_columns = host_columns
        self.service_columns = service_columns

        self._custom_toplevel: bool | None = None
        self._custom_sort_index: int | None = None

    @property
    def title(self) -> str:
        return str(self._title)

    def render(
        self,
        what: Literal["host", "service"],
        row: Row,
        tags: Sequence[TagID],
        custom_vars: Mapping[str, str],
    ) -> (
        None
        | IconSpec
        | HTML
        | tuple[IconSpec, str]
        | tuple[IconSpec, str, str]
        | tuple[IconSpec, str, str | None]
        | tuple[IconSpec, str, tuple[str, str]]
    ):
        return self._render_func(what, row, tags, custom_vars)

    @property
    def toplevel(self) -> bool:
        if self._custom_toplevel is not None:
            return self._custom_toplevel
        return self._toplevel

    @property
    def sort_index(self) -> int:
        if self._custom_sort_index is not None:
            return self._custom_sort_index
        return self._sort_index

    def override_toplevel(self, toplevel: bool | None) -> None:
        self._custom_toplevel = toplevel

    def override_sort_index(self, sort_index: int | None) -> None:
        self._custom_sort_index = sort_index
