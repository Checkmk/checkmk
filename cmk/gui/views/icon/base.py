#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import abc
from collections.abc import Sequence

from cmk.utils.tags import TagID

from cmk.gui.type_defs import ColumnName
from cmk.gui.type_defs import Icon as IconSpec
from cmk.gui.type_defs import Row
from cmk.gui.utils.html import HTML


class Icon(abc.ABC):
    _custom_toplevel: bool | None = None
    _custom_sort_index: int | None = None

    @classmethod
    def type(cls) -> str:
        return "icon"

    @classmethod
    @abc.abstractmethod
    def title(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def override_toplevel(cls, toplevel: bool) -> None:
        cls._custom_toplevel = toplevel

    @classmethod
    def override_sort_index(cls, sort_index: int) -> None:
        cls._custom_sort_index = sort_index

    @classmethod
    @abc.abstractmethod
    def ident(cls) -> str:
        raise NotImplementedError()

    @abc.abstractmethod
    def render(
        self,
        what: str,
        row: Row,
        tags: list[TagID],
        custom_vars: dict[str, str],
    ) -> None | IconSpec | HTML | tuple[IconSpec, str] | tuple[IconSpec, str, str]:
        raise NotImplementedError()

    def columns(self) -> Sequence[ColumnName]:
        """List of livestatus columns needed by this icon idependent of
        the queried table. The table prefix will be added to each column
        (e.g. name -> host_name)"""
        return []

    def host_columns(self) -> list[str]:
        """List of livestatus columns needed by this icon when it is
        displayed for a host row. The prefix host_ will be added to each
        column (e.g. name -> host_name)"""
        return []

    def service_columns(self) -> list[str]:
        """List of livestatus columns needed by this icon when it is
        displayed for a service row. The prefix host_ will be added to each
        column (e.g. description -> service_description)"""
        return []

    def default_toplevel(self) -> bool:
        """Whether or not to display the icon in the column or the action menu"""
        return False

    def default_sort_index(self) -> int:
        return 30

    def toplevel(self) -> bool:
        if self._custom_toplevel is not None:
            return self._custom_toplevel
        return self.default_toplevel()

    def sort_index(self) -> int:
        if self._custom_sort_index is not None:
            return self._custom_sort_index
        return self.default_sort_index()
