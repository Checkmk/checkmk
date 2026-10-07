#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

import pytest

from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.painter import Cell, EmptyCell, InternalPainter, PainterContext, PainterRegistry
from cmk.gui.painter.legacy import Painter
from cmk.gui.type_defs import ColumnName, ColumnSpec, Row
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import FixedValue
from cmk.gui.view_utils import CellSpec
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context

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


_LATE_COLUMNS: list[ColumnName] = []


class _LegacyPainterWithLateColumns(_LegacyPainter):
    @property
    @override
    def columns(self) -> Sequence[ColumnName]:
        return list(_LATE_COLUMNS)


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
    return Cell(ColumnSpec(name="legacy"), None, registry, make_painter_context(_PERMISSIONS), None)


def test_register_returns_the_legacy_class() -> None:
    assert PainterRegistry().register(_LegacyPainter) is _LegacyPainter


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_is_registered_by_its_ident() -> None:
    assert list(_registry()) == ["legacy"]


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_title_reaches_the_cell() -> None:
    assert _cell(_registry()).title(use_short=False) == "Legacy"


def test_legacy_painter_has_its_title_as_static_title() -> None:
    assert str(_registry()["legacy"].static_title) == "Legacy"


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_renders_with_the_permissions_of_its_cell() -> None:
    assert _cell(_registry()).render_content({"host_name": "heute"}, user) == (
        "",
        "own permissions",
    )


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_reads_its_columns_on_access() -> None:
    registry = PainterRegistry()
    registry.register(_LegacyPainterWithLateColumns)
    _LATE_COLUMNS.append("host_name")
    try:
        assert registry["legacy"].columns == ["host_name"]
    finally:
        _LATE_COLUMNS.clear()


@pytest.mark.usefixtures("request_context")
def test_legacy_painter_keeps_its_uuid_column() -> None:
    registry = PainterRegistry()
    registry.register(_LegacyPainterWithUUIDColumn)
    assert registry["legacy"].uuid_col(_cell(registry)) == "legacy_uuid"


def _render_host_address(
    row: Row, _cell: Cell, _user: LoggedInUser, _context: PainterContext
) -> CellSpec:
    return "", row["host_address"]


def _host_address_registry() -> PainterRegistry:
    registry = PainterRegistry()
    registry.register(
        InternalPainter(ident="host_address", title="Host address", render=_render_host_address)
    )
    return registry


def test_painter_is_registered_by_its_ident() -> None:
    assert list(_host_address_registry()) == ["host_address"]


def test_painter_renders_through_a_cell() -> None:
    cell = Cell(
        ColumnSpec(name="host_address"),
        None,
        _host_address_registry(),
        make_painter_context(_PERMISSIONS),
        None,
    )
    assert cell.render_content({"host_address": "10.0.0.1"}, user) == ("", "10.0.0.1")


def test_painter_that_is_not_groupable_puts_all_rows_into_one_group() -> None:
    painter = InternalPainter(
        ident="icons", title="Icons", groupable=False, render=_render_host_address
    )
    cell = EmptyCell()
    assert painter.group_by(
        {"host_address": "10.0.0.1"}, cell, make_painter_context(_PERMISSIONS)
    ) == ("",)


def test_painter_shows_its_static_tooltip_title() -> None:
    painter = InternalPainter(
        ident="host_address",
        title="Host address",
        tooltip_title="Primary address",
        render=_render_host_address,
    )
    cell = EmptyCell()
    assert painter.tooltip_title(cell, make_painter_context(_PERMISSIONS)) == "Primary address"


_HOST_ADDRESS_PARAMETERS = FixedValue(value=None)


def _host_address_parameters(_context: PainterContext) -> FixedValue[None]:
    return _HOST_ADDRESS_PARAMETERS


def test_painter_builds_its_parameters_from_the_context() -> None:
    painter = InternalPainter(
        ident="host_address",
        title="Host address",
        parameters=_host_address_parameters,
        render=_render_host_address,
    )
    assert painter.parameters(make_painter_context(_PERMISSIONS)) is _HOST_ADDRESS_PARAMETERS


def test_painter_returns_its_static_parameters() -> None:
    painter = InternalPainter(
        ident="host_address",
        title="Host address",
        parameters=_HOST_ADDRESS_PARAMETERS,
        render=_render_host_address,
    )
    assert painter.parameters(make_painter_context(_PERMISSIONS)) is _HOST_ADDRESS_PARAMETERS
