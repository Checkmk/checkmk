#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.http import response
from cmk.gui.painter import Cell, InternalPainter
from cmk.gui.painter_options import PainterOptions
from cmk.gui.type_defs import ColumnSpec, GroupSpec, Row, ViewSpec
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.layout.base import Layout
from cmk.gui.views.layout.layouts import (
    create_matrices,
    get_group_spec,
    LayoutBalancedBoxes,
    LayoutBalancedGraphBoxes,
    LayoutMatrix,
    LayoutSingleDataset,
    LayoutTable,
    LayoutTiled,
)
from cmk.gui.views.store import multisite_builtin_views
from tests.testlib.unit.gui.web_test_app import SetConfig
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


@pytest.mark.parametrize(
    "group_spec, expected_group_spec, service_name",
    [
        pytest.param(
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            "Interface 1",
            id="non-capturing groups case 1 (SUP-19435)",
        ),
        pytest.param(
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            GroupSpec(
                title="Hardware",
                pattern="(?i:cpu)|(?i:interface).*",
                min_items=2,
            ),
            "CPU load",
            id="non-capturing groups case 2 (SUP-19435)",
        ),
        pytest.param(
            GroupSpec(
                title="CPU",
                pattern="(?!.*(CPU)).*",
                min_items=2,
            ),
            GroupSpec(
                title="CPU",
                pattern="(?!.*(CPU)).*",
                min_items=2,
            ),
            "CPU load",
            id="non-capturing groups case 3 (SUP-21609)",
        ),
        pytest.param(
            GroupSpec(
                title=r"Oracle instance \1",
                pattern="ORA ([A-Za-z0-9]+).*",
                min_items=2,
            ),
            GroupSpec(
                title="Oracle instance 1337",
                pattern="ORA ([A-Za-z0-9]+).*",
                min_items=2,
            ),
            "ORA 1337",
            id="match group replacement (SUP-13124)",
        ),
        pytest.param(
            GroupSpec(
                title="LocalChecks",
                pattern="local_",
                min_items=2,
            ),
            GroupSpec(
                title="LocalChecks",
                pattern="local_",
                min_items=2,
            ),
            r"local_\PTest",
            id=r"Bad escape \P (SUP-14585)",
        ),
        pytest.param(
            GroupSpec(
                title=r"LocalChecks \1",
                pattern="local_(.*)",
                min_items=2,
            ),
            GroupSpec(
                title=r"LocalChecks \PTest",
                pattern="local_(.*)",
                min_items=2,
            ),
            r"local_\PTest",
            id=r"Bad escape \P (SUP-14585)",
        ),
        pytest.param(
            GroupSpec(
                title=r"Foo \1 Bar \2",
                pattern=r"my_(\d+)_services_(\d+)",
                min_items=2,
            ),
            GroupSpec(
                title=r"Foo 10 Bar 20",
                pattern=r"my_(\d+)_services_(\d+)",
                min_items=2,
            ),
            "my_10_services_20",
            id="two match groups replacement",
        ),
    ],
)
def test_get_group_spec(
    group_spec: GroupSpec, expected_group_spec: GroupSpec, service_name: str
) -> None:
    assert get_group_spec(group_spec, service_name) == expected_group_spec


def _column_painter(ident: str, column: str) -> InternalPainter:
    return InternalPainter(
        ident=ident,
        title=f"{ident} title",
        columns=[column],
        render=lambda row, _cell, _user, _context: (f"{ident}_class", str(row.get(column, ""))),
    )


PAINTERS = {
    "host": _column_painter("host", "host_name"),
    "service": _column_painter("service", "service_description"),
    "state": _column_painter("state", "service_state"),
}
PERMISSIONS = UserPermissions({}, {}, {}, [])
INTERFACE_GROUPING = [GroupSpec(title="Interfaces", pattern="Interface", min_items=2)]


def _cells(*names: str) -> list[Cell]:
    context = make_painter_context(PERMISSIONS)
    return [Cell(ColumnSpec(name=name), None, PAINTERS, context, None) for name in names]


def _service(host: str, service: str, state: int) -> Row:
    return {
        "site": "local",
        "host_name": host,
        "service_description": service,
        "service_state": state,
        "service_has_been_checked": 1,
    }


def _view() -> ViewSpec:
    view = multisite_builtin_views["allservices"].copy()
    view["column_headers"] = "pergroup"
    return view


def _render(
    layout: Layout,
    rows: Sequence[Row],
    *,
    cells: Sequence[Cell],
    group_cells: Sequence[Cell] = (),
    num_columns: int = 1,
    show_checkboxes: bool = False,
) -> str:
    with output_funnel.plugged():
        layout.render(
            list(rows),
            _view(),
            group_cells,
            cells,
            num_columns,
            show_checkboxes,
            PERMISSIONS,
        )
        return "".join(output_funnel.drain())


ROWS = [
    _service("alpha", "CPU", 0),
    _service("alpha", "Memory", 2),
    _service("beta", "CPU", 0),
]


@pytest.mark.usefixtures("request_context")
def test_a_single_dataset_lists_each_column_title_next_to_its_values() -> None:
    rendered = _render(LayoutSingleDataset(), ROWS, num_columns=2, cells=_cells("service", "state"))

    assert "service title" in rendered
    assert rendered.count('<tr class="gap">') == 1
    assert rendered.count('style="border-style: none;"') == 2
    assert "Memory" in rendered


@pytest.mark.usefixtures("request_context")
def test_a_single_column_table_colors_each_line_by_service_state() -> None:
    rendered = _render(LayoutTable(), ROWS, cells=_cells("service", "state"))

    assert 'class="data odd2"' in rendered


@pytest.mark.usefixtures("request_context")
def test_a_grouped_table_shows_a_header_per_group() -> None:
    rendered = _render(
        LayoutTable(),
        ROWS,
        group_cells=_cells("host"),
        num_columns=2,
        cells=_cells("service", "state"),
    )

    assert rendered.count('<tr class="groupheader">') == 2
    assert 'class="fillup"' in rendered


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_table_with_checkboxes_makes_its_rows_selectable() -> None:
    rendered = _render(LayoutTable(), ROWS, show_checkboxes=True, cells=_cells("service", "state"))

    assert 'name="_toggle_group"' in rendered
    assert rendered.count('type="checkbox"') == len(ROWS)


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_a_table_folds_ok_services_of_a_configured_group(set_config: SetConfig) -> None:
    rows = [_service("alpha", f"Interface {i}", 0) for i in range(3)] + [
        _service("alpha", "Interface 3", 2)
    ]

    with set_config(service_view_grouping=INTERFACE_GROUPING):
        rendered = _render(
            LayoutTable(),
            rows,
            group_cells=_cells("host"),
            cells=_cells("service", "state"),
        )

    assert "Interfaces (3)" in rendered
    assert "display:none" in rendered


@pytest.mark.parametrize(
    "layout, box_class",
    [
        pytest.param(LayoutBalancedBoxes(), "boxlayout", id="balanced boxes"),
        pytest.param(LayoutBalancedGraphBoxes(), "boxlayout graph", id="graph boxes"),
    ],
)
@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_boxes_spread_the_groups_over_the_columns(layout: Layout, box_class: str) -> None:
    rendered = _render(
        layout,
        ROWS,
        group_cells=_cells("host"),
        num_columns=2,
        show_checkboxes=True,
        cells=_cells("service", "state"),
    )

    assert f'class="{box_class}"' in rendered
    assert rendered.count('class="boxcolumn"') == 2


@pytest.mark.usefixtures("request_context", "with_admin_login", "patch_theme")
def test_boxes_fold_ok_services_of_a_configured_group(set_config: SetConfig) -> None:
    rows = [_service("alpha", f"Interface {i}", 0) for i in range(3)]

    with set_config(service_view_grouping=INTERFACE_GROUPING):
        rendered = _render(
            LayoutBalancedBoxes(),
            rows,
            group_cells=_cells("host"),
            cells=_cells("service", "state"),
        )

    assert "Interfaces (3)" in rendered


@pytest.mark.usefixtures("request_context")
def test_a_tile_is_colored_by_the_state_of_its_service() -> None:
    rows = [ROWS[1], {**ROWS[0], "service_has_been_checked": 0}]

    rendered = _render(
        LayoutTiled(),
        rows,
        group_cells=_cells("host"),
        cells=_cells("service", "state"),
    )

    assert "sstate2" in rendered
    assert "sstatep" in rendered


@pytest.mark.usefixtures("request_context")
def test_a_host_tile_is_colored_by_the_host_state() -> None:
    rows: list[Row] = [
        {"site": "local", "host_name": "alpha", "host_state": 1, "host_has_been_checked": 1},
        {"site": "local", "host_name": "beta", "host_has_been_checked": 0},
    ]

    rendered = _render(LayoutTiled(), rows, cells=_cells("host"))

    assert "hhstate1" in rendered
    assert "hhstatep" in rendered


@pytest.mark.usefixtures("request_context")
def test_a_matrix_marks_the_value_that_differs_from_the_majority() -> None:
    rows = [*ROWS, _service("beta", "Memory", 0), _service("gamma", "Memory", 0)]

    rendered = _render(
        LayoutMatrix(),
        rows,
        group_cells=_cells("host"),
        cells=_cells("service", "state"),
        num_columns=3,
    )

    assert "state_class minority" in rendered
    assert rendered.count('class="matrixhead"') == 1


@pytest.mark.usefixtures("request_context")
def test_a_matrix_can_omit_rows_without_any_difference() -> None:
    PainterOptions.get_instance().set("matrix_omit_uniform", True)

    rendered = _render(
        LayoutMatrix(),
        [*ROWS, _service("beta", "Memory", 0)],
        group_cells=_cells("host"),
        cells=_cells("service", "state"),
        num_columns=2,
    )

    assert "Memory" in rendered
    assert ">CPU<" not in rendered


@pytest.mark.usefixtures("request_context")
def test_a_matrix_nests_a_table_for_several_value_columns() -> None:
    rendered = _render(
        LayoutMatrix(), ROWS, group_cells=_cells("host"), cells=_cells("service", "state", "host")
    )

    assert 'class="cell"' in rendered


@pytest.mark.usefixtures("request_context")
def test_a_matrix_wraps_into_several_tables_after_the_column_limit() -> None:
    matrices = list(create_matrices(ROWS, _cells("host"), _cells("service", "state"), 1))

    assert [[host for host, _row in groups] for groups, _ids, _cells_ in matrices] == [
        [("alpha",)],
        [("beta",)],
    ]


@pytest.mark.parametrize(
    "group_cells, cells",
    [
        pytest.param(("host",), ("service",), id="a single column"),
        pytest.param((), ("service", "state"), id="no group column"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_a_matrix_needs_a_group_column_and_two_columns(
    group_cells: Sequence[str], cells: Sequence[str]
) -> None:
    with pytest.raises(MKGeneralException):
        list(create_matrices(ROWS, _cells(*group_cells), _cells(*cells), None))


@pytest.mark.usefixtures("request_context")
def test_a_matrix_exports_one_csv_line_per_service() -> None:
    LayoutMatrix().csv_export(
        ROWS,
        _view(),
        _cells("host"),
        _cells("service", "state"),
        PERMISSIONS,
        table_row_limit=100,
    )

    lines = response.get_data(as_text=True).splitlines()
    assert [line.split(";")[0] for line in lines] == ["", "host title", "CPU", "Memory"]
