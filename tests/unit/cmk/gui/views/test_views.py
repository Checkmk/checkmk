#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from typing import Any

import pytest

import cmk.ccc.version as cmk_version
import cmk.gui.plugins.views
import cmk.gui.views
from cmk.ccc.site import SiteId
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource, RowTable
from cmk.gui.display_options import display_options
from cmk.gui.exporter import exporter_registry
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import (
    all_painters,
    Cell,
    Painter,
    PainterRegistry,
    register_painter,
)
from cmk.gui.painter.v0 import registry as painter_registry_module
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import painter_option_registry, PainterOptions
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import ColumnSpec, SorterSpec
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.valuespec import ValueSpec
from cmk.gui.view import View
from cmk.gui.views import command
from cmk.gui.views.command import command_group_registry, command_registry
from cmk.gui.views.command import group as group_module
from cmk.gui.views.command import registry as registry_module
from cmk.gui.views.inventory.registry import inventory_displayhints
from cmk.gui.views.layout import layout_registry
from cmk.gui.views.page_show_view import get_limit
from cmk.gui.views.store import multisite_builtin_views
from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection
from tests.unit.cmk.web_test_app import WebTestAppForCMK


def test_registered_painter_options(request_context: None) -> None:
    expected = [
        "aggr_expand",
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


def test_registered_layouts() -> None:
    expected = [
        "boxed",
        "boxed_graph",
        "dataset",
        "matrix",
        "mobiledataset",
        "mobilelist",
        "mobiletable",
        "table",
        "tiled",
    ]

    names = layout_registry.keys()
    assert sorted(expected) == sorted(names)


def test_layout_properties() -> None:
    expected = {
        "boxed": {"checkboxes": True, "title": "Balanced boxes"},
        "boxed_graph": {"checkboxes": True, "title": "Balanced graph boxes"},
        "dataset": {"checkboxes": False, "title": "Single dataset"},
        "matrix": {
            "checkboxes": False,
            "has_csv_export": True,
            "options": ["matrix_omit_uniform"],
            "title": "Matrix",
        },
        "mobiledataset": {"checkboxes": False, "title": "Mobile: Dataset"},
        "mobilelist": {"checkboxes": False, "title": "Mobile: List"},
        "mobiletable": {"checkboxes": False, "title": "Mobile: Table"},
        "table": {"checkboxes": True, "title": "Table"},
        "tiled": {"checkboxes": True, "title": "Tiles"},
    }

    for ident, spec in expected.items():
        plugin = layout_registry[ident]()
        assert isinstance(plugin.title, str)
        assert spec["title"] == plugin.title
        assert spec["checkboxes"] == plugin.can_display_checkboxes
        assert spec.get("has_csv_export", False) == plugin.has_individual_csv_export


def test_get_layout_choices() -> None:
    choices = layout_registry.get_choices()
    assert sorted(choices) == sorted(
        [
            ("matrix", "Matrix"),
            ("boxed_graph", "Balanced graph boxes"),
            ("dataset", "Single dataset"),
            ("tiled", "Tiles"),
            ("table", "Table"),
            ("boxed", "Balanced boxes"),
            ("mobiledataset", "Mobile: Dataset"),
            ("mobiletable", "Mobile: Table"),
            ("mobilelist", "Mobile: List"),
        ]
    )


def test_registered_exporters() -> None:
    expected = [
        "csv",
        "csv_export",
        "json",
        "json_export",
        "jsonp",
        "python",
        "python-raw",
    ]
    names = exporter_registry.keys()
    assert sorted(expected) == sorted(names)


def test_registered_command_groups() -> None:
    expected = [
        "acknowledge",
        "aggregations",
        "downtimes",
        "fake_check",
        "various",
    ]

    names = command_group_registry.keys()
    assert sorted(expected) == sorted(names)


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


def test_registered_commands() -> None:
    expected: dict[str, dict[str, Any]] = {
        "acknowledge": {
            "group": "acknowledge",
            "permission": "action.acknowledge",
            "tables": ["host", "service", "aggr"],
            "title": "Acknowledge problems",
        },
        "freeze_aggregation": {
            "group": "aggregations",
            "permission": "action.aggregation_freeze",
            "tables": ["aggr"],
            "title": "Freeze aggregations",
        },
        "ec_custom_actions": {
            "permission": "mkeventd.actions",
            "tables": ["event"],
            "title": "Custom action",
        },
        "remove_acknowledgments": {
            "group": "acknowledge",
            "permission": "action.acknowledge",
            "tables": ["host", "service", "aggr"],
            "title": "Remove acknowledgments",
        },
        "remove_comments": {
            "permission": "action.addcomment",
            "tables": ["comment"],
            "title": "Delete comments",
        },
        "remove_downtimes_hosts_services": {
            "permission": "action.downtimes",
            "tables": ["host", "service"],
            "title": "Remove downtimes",
        },
        "remove_downtimes": {
            "permission": "action.downtimes",
            "tables": ["downtime"],
            "title": "Remove downtimes",
        },
        "schedule_downtimes": {
            "permission": "action.downtimes",
            "tables": ["host", "service", "aggr"],
            "title": "Schedule downtimes",
        },
        "ec_archive_events_of_host": {
            "permission": "mkeventd.archive_events_of_hosts",
            "tables": ["service"],
            "title": "Archive events of hosts",
        },
        "ec_change_state": {
            "permission": "mkeventd.changestate",
            "tables": ["event"],
            "title": "Change state",
        },
        "clear_modified_attributes": {
            "permission": "action.clearmodattr",
            "tables": ["host", "service"],
            "title": "Reset modified attributes",
        },
        "send_custom_notification": {
            "permission": "action.customnotification",
            "tables": ["host", "service"],
            "title": "Send custom notification",
        },
        "ec_archive_event": {
            "permission": "mkeventd.delete",
            "tables": ["event"],
            "title": "Archive event",
        },
        "add_comment": {
            "permission": "action.addcomment",
            "tables": ["host", "service"],
            "title": "Add comment",
        },
        "toggle_passive_checks": {
            "permission": "action.enablechecks",
            "tables": ["host", "service"],
            "title": "Enable/Disable passive checks",
        },
        "toggle_active_checks": {
            "permission": "action.enablechecks",
            "tables": ["host", "service"],
            "title": "Enable/Disable active checks",
        },
        "fake_check_result": {
            "group": "fake_check",
            "permission": "action.fakechecks",
            "tables": ["host", "service"],
            "title": "Fake check results",
        },
        "notifications": {
            "permission": "action.notifications",
            "tables": ["host", "service"],
            "title": "Enable/disable notifications",
        },
        "reschedule": {
            "permission": "action.reschedule",
            "row_stats": True,
            "tables": ["host", "service"],
            "title": "Reschedule active checks",
        },
        "ec_update_event": {
            "permission": "mkeventd.update",
            "tables": ["event"],
            "title": "Update & acknowledge",
        },
        "delete_crash_reports": {
            "permission": "action.delete_crash_report",
            "tables": ["crash"],
            "title": "Delete crash reports",
        },
    }

    if cmk_version.edition(paths.omd_root) is not cmk_version.Edition.CRE:
        expected.update(
            {
                "edit_downtimes": {
                    "permission": "action.downtimes",
                    "tables": ["downtime"],
                    "title": "Edit downtimes",
                },
            }
        )

    names = command_registry.keys()
    assert sorted(expected.keys()) == sorted(names)

    for cmd in command_registry.values():
        cmd_spec = expected[cmd.ident]
        assert cmd.title == cmd_spec["title"]
        assert cmd.tables == cmd_spec["tables"], cmd.ident
        assert cmd.permission.name == cmd_spec["permission"]


def test_legacy_register_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry_module, "command_registry", registry := command.CommandRegistry())

    def render() -> None:
        pass

    def action():
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


def test_painter_export_title(monkeypatch: pytest.MonkeyPatch, view: View) -> None:
    registered_painters = all_painters(active_config.tags.tag_groups)
    user_permissions = UserPermissions({}, {}, {}, [])
    painters: list[Painter] = [
        painter_class(
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
            user_permissions=user_permissions,
        )
        for painter_class in registered_painters.values()
    ]
    painters_and_cells: list[tuple[Painter, Cell]] = [
        (
            painter,
            Cell(
                ColumnSpec(name=painter.ident),
                None,
                registered_painters,
                user_permissions,
            ),
        )
        for painter in painters
    ]

    dummy_ident: str = "einszwo"
    for painter, cell in painters_and_cells:
        cell._painter_params = {"ident": dummy_ident}
        expected_title: str = painter.ident
        if painter.ident in ["host_custom_variable", "service_custom_variable"]:
            expected_title += "_%s" % dummy_ident
        assert painter.export_title(cell) == expected_title


def test_legacy_register_painter(monkeypatch: pytest.MonkeyPatch, view: View) -> None:
    monkeypatch.setattr(painter_registry_module, "painter_registry", PainterRegistry())

    def rendr(row):
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
    painter = registered_painters["abc"](
        config=active_config,
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
        user_permissions=(user_permissions := UserPermissions({}, {}, {}, [])),
    )
    dummy_cell = Cell(ColumnSpec(name=painter.ident), None, registered_painters, user_permissions)
    assert isinstance(painter, Painter)
    assert painter.ident == "abc"
    assert painter.title(dummy_cell) == "A B C"
    assert painter.short_title(dummy_cell) == "ABC"
    assert painter.columns == ["x"]
    assert painter.sorter == "aaaa"
    assert painter.painter_options == ["opt1"]
    assert painter.printable is False
    assert painter.render(row={}, cell=dummy_cell, user=user) == ("abc", "xyz")
    assert painter.group_by(row={}, cell=dummy_cell) == "xyz"


def test_create_view_basics() -> None:
    view_name = "allhosts"
    view_spec = multisite_builtin_views[view_name]
    view = View(view_name, view_spec, view_spec.get("context", {}), UserPermissions({}, {}, {}, []))

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
    "limit,ignore_soft_limit,ignore_hard_limit,result",
    [
        (None, False, False, 1000),
        ("soft", False, False, 1000),
        ("hard", False, False, 1000),
        ("none", False, False, 1000),
        ("soft", True, False, 1000),
        ("hard", True, False, 5000),
        # Strange. Shouldn't this stick to the hard limit?
        ("none", True, False, 1000),
        ("soft", True, True, 1000),
        ("hard", True, True, 5000),
        ("none", True, True, None),
    ],
)
def test_gui_view_row_limit(
    limit: str, ignore_soft_limit: bool, ignore_hard_limit: bool, result: int | None
) -> None:
    assert (
        get_limit(
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


def test_get_inventory_display_hint() -> None:
    hint = inventory_displayhints.get(".software.packages:*.summary")
    assert isinstance(hint, dict)


@pytest.mark.usefixtures("suppress_license_expiry_header", "patch_theme", "suppress_license_banner")
def test_view_page(
    logged_in_admin_wsgi_app: WebTestAppForCMK, mock_livestatus: MockLiveStatusConnection
) -> None:
    wsgi_app = logged_in_admin_wsgi_app

    def _prepend(prefix, dict_):
        d = {}
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
        resp = wsgi_app.get("/NO_SITE/check_mk/view.py?view_name=allhosts", status=200)
        assert "heute" in resp.text
        assert "query=null" not in resp.text
        assert str(resp).count("/domain-types/host/collections/all") == 1
