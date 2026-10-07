#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects


from collections.abc import Mapping
from http import HTTPStatus

import pytest

import cmk.gui.views
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config, Config
from cmk.gui.data_source import ABCDataSource, RowTable
from cmk.gui.graphing import vs_graph_render_option_elements
from cmk.gui.logged_in import user
from cmk.gui.painter import (
    all_painters,
    Cell,
    InternalPainter,
    PainterRegistry,
    register_painter,
)
from cmk.gui.painter import registry as painter_registry_module
from cmk.gui.painter_options import painter_option_registry
from cmk.gui.type_defs import ColumnSpec, Row, SorterSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view import View
from cmk.gui.views import command
from cmk.gui.views.command import group as group_module
from cmk.gui.views.command import registry as registry_module
from cmk.gui.views.graph import _LEGACY_ONLY_RENDER_OPTIONS
from cmk.gui.views.page_show_view import get_limit
from cmk.gui.views.store import multisite_builtin_views
from cmk.livestatus_client.testing import MockLiveStatusConnection
from cmk.web.utils.request_cache import RequestCache
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK
from tests.unit.cmk.gui.helpers.painter_context_test_helper import make_painter_context


@pytest.mark.usefixtures("request_context")
def test_registered_painter_options() -> None:
    expected = [
        "aggr_expand",
        "aggr_onlydiff",
        "aggr_onlyproblems",
        "aggr_treetype",
        "aggr_wrap",
        "matrix_omit_uniform",
        "pnp_timerange",
        "show_internal_tree_paths",
        "ts_date",
        "ts_format",
        "graph_render_options",
        "refresh",
        "num_columns",
        "show_internal_graph_and_metric_ids",
    ]

    names = painter_option_registry.keys()
    assert sorted(expected) == sorted(names)

    for cls in painter_option_registry.values():
        vs = cls.valuespec
        assert isinstance(vs, ValueSpec)


def test_legacy_only_render_options_name_existing_options() -> None:
    # A stale key would silently stop excluding anything from the graph views' display options.
    assert set(_LEGACY_ONLY_RENDER_OPTIONS) <= {
        key for key, _vs in vs_graph_render_option_elements()
    }


def test_legacy_register_command_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        group_module, "command_group_registry", registry := command.CommandGroupRegistry()
    )
    command.register_command_group("abc", "A B C", 123)

    group = registry["abc"]()
    assert isinstance(group, command.CommandGroup)
    assert group.ident == "abc"
    assert group.title == "A B C"
    assert group.sort_index == 123


def test_legacy_register_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry_module, "command_registry", registry := command.CommandRegistry())

    def render() -> None:
        pass

    def action() -> None:
        pass

    command.register_legacy_command(
        {
            "tables": ["tabl"],
            "permission": "general.use",
            "title": "Bla Bla",
            "render": render,
            "action": action,
        }
    )

    cmd = registry["blabla"]
    assert isinstance(cmd, command.Command)
    assert cmd.ident == "blabla"
    assert cmd.title == "Bla Bla"
    assert cmd.permission == cmk.gui.default_permissions.PermissionGeneralUse


@pytest.mark.usefixtures("monkeypatch", "view")
def test_painter_export_title() -> None:
    registered_painters = all_painters(active_config.tags.tag_groups)
    user_permissions = UserPermissions({}, {}, {}, [])
    painters: list[InternalPainter] = list(registered_painters.values())
    painters_and_cells: list[tuple[InternalPainter, Cell]] = [
        (
            painter,
            Cell(
                ColumnSpec(name=painter.ident),
                None,
                registered_painters,
                make_painter_context(user_permissions),
                RequestCache(Config()),
            ),
        )
        for painter in painters
    ]

    dummy_ident: str = "einszwo"
    for painter, cell in painters_and_cells:
        cell._painter_params = {"ident": dummy_ident}  # noqa: SLF001
        expected_title: str = painter.ident
        if painter.ident in ["host_custom_variable", "service_custom_variable"]:
            expected_title += "_%s" % dummy_ident
        assert painter.export_title(cell) == expected_title


@pytest.mark.usefixtures("view")
def test_legacy_register_painter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(painter_registry_module, "painter_registry", PainterRegistry())

    def rendr(row: Row) -> tuple[str, str]:
        return ("abc", "xyz")

    register_painter(
        "abc",
        {
            "title": "A B C",
            "short": "ABC",
            "columns": ["x"],
            "sorter": "aaaa",
            "options": ["opt1"],
            "printable": False,
            "paint": rendr,
            "groupby": "xyz",
        },
    )

    registered_painters = all_painters(active_config.tags.tag_groups)
    painter = registered_painters["abc"]
    dummy_cell = Cell(
        ColumnSpec(name=painter.ident),
        None,
        registered_painters,
        make_painter_context(UserPermissions({}, {}, {}, [])),
        None,
    )
    context = dummy_cell.painter_context()
    assert isinstance(painter, InternalPainter)
    assert painter.ident == "abc"
    assert painter.title(dummy_cell, context) == "A B C"
    assert painter.short_title(dummy_cell, context) == "ABC"
    assert painter.columns == ["x"]
    assert painter.sorter == "aaaa"
    assert painter.painter_options == ["opt1"]
    assert painter.printable is False
    assert painter.render(row={}, cell=dummy_cell, user=user, context=context) == ("abc", "xyz")
    assert painter.group_by(row={}, cell=dummy_cell, context=context) == "xyz"


def test_create_view_basics() -> None:
    view_name = "allhosts"
    view_spec = multisite_builtin_views[view_name]
    view = View(
        view_name,
        view_spec,
        view_spec.get("context", {}),
        make_painter_context(UserPermissions({}, {}, {}, [])),
        RequestCache(Config()),
    )

    assert view.name == view_name
    assert view.spec == view_spec
    assert isinstance(view.datasource, ABCDataSource)
    assert isinstance(view.datasource.table, RowTable)
    assert view.row_limit is None
    assert view.user_sorters is None
    assert view.want_checkboxes is False
    assert view.only_sites is None


def test_view_row_limit(view: View) -> None:
    assert view.row_limit is None
    view.row_limit = 101
    assert view.row_limit == 101


@pytest.mark.parametrize(
    "spec_limit,limit,ignore_soft_limit,ignore_hard_limit,result",
    [
        (0, None, False, False, 1000),
        (0, "soft", False, False, 1000),
        (0, "hard", False, False, 1000),
        (0, "none", False, False, 1000),
        (0, "soft", True, False, 1000),
        (0, "hard", True, False, 5000),
        # Strange. Shouldn't this stick to the hard limit?
        (0, "none", True, False, 1000),
        (0, "soft", True, True, 1000),
        (0, "hard", True, True, 5000),
        (0, "none", True, True, None),
        (10, None, False, False, 10),
        (10, "none", True, True, 10),
        (10, "hard", True, False, 10),
    ],
)
def test_gui_view_row_limit(
    spec_limit: int,
    limit: str,
    ignore_soft_limit: bool,
    ignore_hard_limit: bool,
    result: int | None,
) -> None:
    assert (
        get_limit(
            view_spec_row_limit=spec_limit,
            request_limit_mode=limit,
            soft_query_limit=1000,
            may_ignore_soft_limit=ignore_soft_limit,
            hard_query_limit=5000,
            may_ignore_hard_limit=ignore_hard_limit,
        )
        == result
    )


def test_view_only_sites(view: View) -> None:
    assert view.only_sites is None
    view.only_sites = [SiteId("unit")]
    assert view.only_sites == [SiteId("unit")]


def test_view_user_sorters(view: View) -> None:
    assert view.user_sorters is None
    view.user_sorters = [SorterSpec(sorter="abc", negate=True)]
    assert view.user_sorters == [SorterSpec(sorter="abc", negate=True)]


def test_view_want_checkboxes(view: View) -> None:
    assert view.want_checkboxes is False
    view.want_checkboxes = True
    assert view.want_checkboxes is True


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
def test_view_page(
    logged_in_admin_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
) -> None:
    wsgi_app = logged_in_admin_wsgi_app

    def _prepend(prefix: str, dict_: Mapping[str, object]) -> dict[str, object]:
        d: dict[str, object] = {}
        for key, value in dict_.items():
            d[key] = value
            d[prefix + key] = value
        return d

    live: MockLiveStatusConnection = mock_livestatus
    live.set_sites(["NO_SITE", "remote"])
    live.add_table(
        "hosts",
        [
            _prepend(
                "host_",
                {
                    "accept_passive_checks": 0,
                    "acknowledged": 0,
                    "action_url_expanded": "",
                    "active_checks_enabled": 1,
                    "address": "127.0.0.1",
                    "check_command": "check-mk-host-smart",
                    "check_type": 0,
                    "comments_with_extra_info": "",
                    "custom_variable_name": "",
                    "custom_variable_names": [
                        "FILENAME",
                        "ADDRESS_FAMILY",
                        "ADDRESS_4",
                        "ADDRESS_6",
                        "TAGS",
                    ],
                    "custom_variable_values": [
                        "/wato/hosts.mk",
                        4,
                        "127.0.0.1",
                        "",
                        "/wato/ auto-piggyback cmk-agent ip-v4 ip-v4-only lan no-snmp prod site:heute tcp",
                    ],
                    "downtimes": "",
                    "downtimes_with_extra_info": "",
                    "filename": "/wato/hosts.mk",
                    "has_been_checked": 1,
                    "icon_image": "",
                    "in_check_period": 1,
                    "in_notification_period": 1,
                    "in_service_period": 1,
                    "is_flapping": 0,
                    "modified_attributes_list": "",
                    "name": "heute",
                    "notes_url_expanded": "",
                    "notifications_enabled": 1,
                    "num_services_crit": 2,
                    "num_services_ok": 37,
                    "num_services_pending": 0,
                    "num_services_unknown": 0,
                    "num_services_warn": 2,
                    "perf_data": "",
                    "pnpgraph_present": 0,
                    "scheduled_downtime_depth": 0,
                    "staleness": 0.833333,
                    "state": 0,
                    "host_labels": {
                        "cmk/os_family": "linux",
                        "cmk/check_mk_server": "yes",
                    },
                },
            )
        ],
    )
    live.expect_query(
        "GET hosts\n"
        "Columns: host_accept_passive_checks host_acknowledged host_action_url_expanded "
        "host_active_checks_enabled host_address host_check_command host_check_type "
        "host_comments_with_extra_info host_custom_variable_names host_custom_variable_values "
        "host_downtimes host_downtimes_with_extra_info host_filename host_has_been_checked "
        "host_icon_image host_in_check_period host_in_notification_period host_in_service_period "
        "host_is_flapping host_labels host_modified_attributes_list host_name host_notes_url_expanded "
        "host_notifications_enabled host_num_services_crit host_num_services_ok "
        "host_num_services_pending host_num_services_unknown host_num_services_warn host_perf_data "
        "host_pnpgraph_present host_scheduled_downtime_depth host_staleness host_state\n"
        "Limit: 1001"
    )
    live.expect_query("GET hosts\nColumns: filename\nStats: state >= 0")
    with live():
        resp = wsgi_app.get("/NO_SITE/check_mk/view.py?view_name=allhosts", status=HTTPStatus.OK)
        assert "heute" in resp.text
        assert "query=null" not in resp.text
