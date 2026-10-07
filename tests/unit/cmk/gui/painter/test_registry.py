#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import override

import pytest

from cmk.gui.i18n import _l
from cmk.gui.logged_in import LoggedInUser, user
from cmk.gui.painter import Cell, EmptyCell, InternalPainter, PainterContext, PainterRegistry
from cmk.gui.painter.legacy import Painter
from cmk.gui.painter.registry import _make_plugin_painter
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


def _paint_nothing(_row: Row) -> CellSpec:
    return "", ""


def _host_name(row: Row) -> str:
    return str(row["host_name"])


def test_plugin_painter_accepts_a_lazy_title() -> None:
    painter = _make_plugin_painter(
        "plugin", {"title": _l("Plug-in"), "columns": [], "paint": _paint_nothing}
    )
    assert painter.title(EmptyCell(), make_painter_context(_PERMISSIONS)) == "Plug-in"


def test_plugin_painter_groups_by_a_function_of_the_row() -> None:
    painter = _make_plugin_painter(
        "plugin",
        {"title": "Plug-in", "columns": [], "paint": _paint_nothing, "groupby": _host_name},
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.group_by({"host_name": "heute"}, EmptyCell(), context) == "heute"


def _no_group(_row: Row) -> None:
    return None


def test_plugin_painter_keeps_a_missing_group_value_of_its_function() -> None:
    painter = _make_plugin_painter(
        "plugin",
        {"title": "Plug-in", "columns": [], "paint": _paint_nothing, "groupby": _no_group},
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.group_by({"host_name": "heute"}, EmptyCell(), context) is None


def _paint_mapping(_row: Row) -> tuple[str, dict[str, str]]:
    return "", {"key": "value"}


def test_plugin_painter_renders_a_mapping() -> None:
    painter = _make_plugin_painter(
        "plugin", {"title": "Plug-in", "columns": [], "paint": _paint_mapping}
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.render({}, EmptyCell(), user, context) == ("", {"key": "value"})


def _paint_host_name(row: Row) -> CellSpec:
    return "", str(row["host_name"])


def _export_host_name_upper(row: Row, _cell: Cell) -> str:
    return str(row["host_name"]).upper()


def test_plugin_painter_exports_the_painted_content_by_default() -> None:
    painter = _make_plugin_painter(
        "plugin", {"title": "Plug-in", "columns": [], "paint": _paint_host_name}
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.export_for_json({"host_name": "heute"}, EmptyCell(), user, context) == "heute"


def test_plugin_painter_exports_through_its_own_export_function() -> None:
    painter = _make_plugin_painter(
        "plugin",
        {
            "title": "Plug-in",
            "columns": [],
            "paint": _paint_host_name,
            "export_for_csv": _export_host_name_upper,
        },
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.export_for_csv({"host_name": "heute"}, EmptyCell(), user, context) == "HEUTE"


def test_plugin_painter_groups_by_its_static_group_value() -> None:
    painter = _make_plugin_painter(
        "plugin", {"title": "Plug-in", "columns": [], "paint": _paint_nothing, "groupby": "dmz"}
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.group_by({"host_name": "heute"}, EmptyCell(), context) == "dmz"


def _export_host_name_length(row: Row, _cell: Cell) -> int:
    return len(str(row["host_name"]))


def test_plugin_painter_exports_a_value_that_is_no_text_as_its_string_to_csv() -> None:
    painter = _make_plugin_painter(
        "plugin",
        {
            "title": "Plug-in",
            "columns": [],
            "paint": _paint_host_name,
            "export_for_csv": _export_host_name_length,
        },
    )
    context = make_painter_context(_PERMISSIONS)
    assert painter.export_for_csv({"host_name": "heute"}, EmptyCell(), user, context) == "5"


def test_plugin_painter_takes_a_missing_short_title_as_its_title() -> None:
    painter = _make_plugin_painter(
        "plugin", {"title": "Plug-in", "short": None, "columns": [], "paint": _paint_nothing}
    )
    assert painter.short_title(EmptyCell(), make_painter_context(_PERMISSIONS)) == "Plug-in"


def test_plugin_painter_validates_its_paint_function_at_registration() -> None:
    with pytest.raises(TypeError):
        _make_plugin_painter("plugin", {"title": "Plug-in", "columns": [], "paint": "host_name"})


def test_plugin_painter_validates_its_spec_at_registration() -> None:
    with pytest.raises(TypeError):
        _make_plugin_painter(
            "plugin", {"title": "Plug-in", "columns": "host_name", "paint": _paint_nothing}
        )
