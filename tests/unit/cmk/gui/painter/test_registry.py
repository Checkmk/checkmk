#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

import pytest

from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.painter import Cell, PainterRegistry
from cmk.gui.painter.base import Painter
from cmk.gui.painter.painters import PainterHostAddress
from cmk.gui.type_defs import ColumnName, ColumnSpec, Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.view_utils import CellSpec

_PERMISSIONS = UserPermissions({}, {}, {}, [])


class _LegacyPainter(Painter):
    @property
    @override
    def ident(self) -> str:
        return "legacy"

    @override
    def title(self, cell: Cell) -> str:
        return "Legacy"

    @property
    @override
    def columns(self) -> Sequence[ColumnName]:
        return ["host_name"]

    @override
    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return "", "own permissions" if self._user_permissions is _PERMISSIONS else "other"


class _RenamedHostAddress(PainterHostAddress):
    @property
    @override
    def ident(self) -> str:
        return "renamed_host_address"


class _LegacyPainterWithUUIDColumn(_LegacyPainter):
    @staticmethod
    @override
    def uuid_col(cell: Cell) -> str:
        return "legacy_uuid"


def _registry() -> PainterRegistry:
    registry = PainterRegistry()
    registry.register(_LegacyPainter)
    return registry


def _cell(registry: PainterRegistry) -> Cell:
    return Cell(ColumnSpec(name="legacy"), None, registry, _PERMISSIONS, None)


def test_register_returns_the_legacy_class() -> None:
    assert PainterRegistry().register(_LegacyPainter) is _LegacyPainter


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_is_registered_by_its_ident() -> None:
    assert list(_registry()) == ["legacy"]


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_title_reaches_the_cell() -> None:
    assert _cell(_registry()).title(use_short=False) == "Legacy"


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_renders_with_the_permissions_of_its_cell() -> None:
    assert _cell(_registry()).render_content({"host_name": "heute"}, user) == (
        "",
        "own permissions",
    )


def test_register_returns_a_built_in_painter_subclass() -> None:
    assert PainterRegistry().register(_RenamedHostAddress) is _RenamedHostAddress


@pytest.mark.usefixtures("request_context")
def test_built_in_painter_subclass_renders_through_a_cell() -> None:
    registry = PainterRegistry()
    registry.register(_RenamedHostAddress)
    cell = Cell(ColumnSpec(name="renamed_host_address"), None, registry, _PERMISSIONS, None)
    assert cell.render_content({"host_address": "10.0.0.1"}, user) == ("", "10.0.0.1")


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_keeps_its_uuid_column() -> None:
    registry = PainterRegistry()
    registry.register(_LegacyPainterWithUUIDColumn)
    assert registry["legacy"].uuid_col(_cell(registry)) == "legacy_uuid"
