#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

from typing import Any, Literal

import pytest

from tests.unit.cmk.web_test_app import WebTestAppForCMK

from livestatus import SiteId

import cmk.ccc.version as cmk_version

from cmk.utils import paths
from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

import cmk.gui.plugins.views
import cmk.gui.views
from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource, RowTable
from cmk.gui.display_options import display_options
from cmk.gui.exporter import exporter_registry
from cmk.gui.http import request, response
from cmk.gui.logged_in import user
from cmk.gui.painter.v0 import all_painters, Cell, Painter, PainterRegistry, register_painter
from cmk.gui.painter.v0 import registry as painter_registry_module
from cmk.gui.painter.v0.helpers import RenderLink
from cmk.gui.painter_options import painter_option_registry, PainterOptions
from cmk.gui.type_defs import ColumnSpec, SorterSpec
from cmk.gui.utils.theme import theme
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
        vs = cls().valuespec
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
    registered_painters = all_painters(active_config)
    painters: list[Painter] = [
        painter_class(
            user=user,
            config=active_config,
            request=request,
            painter_options=PainterOptions.get_instance(),
            theme=theme,
            url_renderer=RenderLink(request, response, display_options),
        )
        for painter_class in registered_painters.values()
    ]
    painters_and_cells: list[tuple[Painter, Cell]] = [
        (painter, Cell(ColumnSpec(name=painter.ident), None, registered_painters))
        for painter in painters
    ]

    dummy_ident: str = "einszwo"
    for painter, cell in painters_and_cells:
        cell._painter_params = {"ident": dummy_ident}  # pylint: disable=protected-access
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

    registered_painters = all_painters(active_config)
    painter = registered_painters["abc"](
        user=user,
        config=active_config,
        request=request,
        painter_options=PainterOptions.get_instance(),
        theme=theme,
        url_renderer=RenderLink(request, response, display_options),
    )
    dummy_cell = Cell(ColumnSpec(name=painter.ident), None, registered_painters)
    assert isinstance(painter, Painter)
    assert painter.ident == "abc"
    assert painter.title(dummy_cell) == "A B C"
    assert painter.short_title(dummy_cell) == "ABC"
    assert painter.columns == ["x"]
    assert painter.sorter == "aaaa"
    assert painter.painter_options == ["opt1"]
    assert painter.printable is False
    assert painter.render(row={}, cell=dummy_cell) == ("abc", "xyz")
    assert painter.group_by(row={}, cell=dummy_cell) == "xyz"


def test_create_view_basics() -> None:
    view_name = "allhosts"
    view_spec = multisite_builtin_views[view_name]
    view = View(view_name, view_spec, view_spec.get("context", {}))

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
    "limit,permissions,result",
    [
        (None, [], 1000),
        ("soft", {}, 1000),
        ("hard", {}, 1000),
        ("none", {}, 1000),
        ("soft", {"general.ignore_soft_limit": True}, 1000),
        ("hard", {"general.ignore_soft_limit": True}, 5000),
        # Strange. Shouldn't this stick to the hard limit?
        ("none", {"general.ignore_soft_limit": True}, 1000),
        ("soft", {"general.ignore_soft_limit": True, "general.ignore_hard_limit": True}, 1000),
        ("hard", {"general.ignore_soft_limit": True, "general.ignore_hard_limit": True}, 5000),
        ("none", {"general.ignore_soft_limit": True, "general.ignore_hard_limit": True}, None),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_gui_view_row_limit(
    monkeypatch: pytest.MonkeyPatch,
    limit: Literal["soft", "hard", "none"] | None,
    permissions: dict[str, bool],
    result: int | None,
) -> None:
    with monkeypatch.context() as m:
        if limit is not None:
            monkeypatch.setitem(request._vars, "limit", limit)
        m.setattr(active_config, "roles", {"nobody": {"permissions": permissions}})
        m.setattr(user, "role_ids", ["nobody"])
        assert get_limit() == result


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


def test_registered_display_hints() -> None:
    expected = [
        ".hardware.",
        ".hardware.chassis.",
        ".hardware.components.",
        ".hardware.components.backplanes:",
        ".hardware.components.backplanes:*.description",
        ".hardware.components.backplanes:*.index",
        ".hardware.components.backplanes:*.location",
        ".hardware.components.backplanes:*.manufacturer",
        ".hardware.components.backplanes:*.model",
        ".hardware.components.backplanes:*.name",
        ".hardware.components.backplanes:*.serial",
        ".hardware.components.backplanes:*.software",
        ".hardware.components.chassis:",
        ".hardware.components.chassis:*.description",
        ".hardware.components.chassis:*.index",
        ".hardware.components.chassis:*.location",
        ".hardware.components.chassis:*.manufacturer",
        ".hardware.components.chassis:*.model",
        ".hardware.components.chassis:*.name",
        ".hardware.components.chassis:*.serial",
        ".hardware.components.chassis:*.software",
        ".hardware.components.containers:",
        ".hardware.components.containers:*.description",
        ".hardware.components.containers:*.index",
        ".hardware.components.containers:*.location",
        ".hardware.components.containers:*.manufacturer",
        ".hardware.components.containers:*.model",
        ".hardware.components.containers:*.name",
        ".hardware.components.containers:*.serial",
        ".hardware.components.containers:*.software",
        ".hardware.components.fans:",
        ".hardware.components.fans:*.description",
        ".hardware.components.fans:*.index",
        ".hardware.components.fans:*.location",
        ".hardware.components.fans:*.manufacturer",
        ".hardware.components.fans:*.model",
        ".hardware.components.fans:*.name",
        ".hardware.components.fans:*.serial",
        ".hardware.components.fans:*.software",
        ".hardware.components.modules:",
        ".hardware.components.modules:*.bootloader",
        ".hardware.components.modules:*.description",
        ".hardware.components.modules:*.firmware",
        ".hardware.components.modules:*.index",
        ".hardware.components.modules:*.location",
        ".hardware.components.modules:*.manufacturer",
        ".hardware.components.modules:*.model",
        ".hardware.components.modules:*.name",
        ".hardware.components.modules:*.serial",
        ".hardware.components.modules:*.software",
        ".hardware.components.modules:*.type",
        ".hardware.components.others:",
        ".hardware.components.others:*.description",
        ".hardware.components.others:*.index",
        ".hardware.components.others:*.location",
        ".hardware.components.others:*.manufacturer",
        ".hardware.components.others:*.model",
        ".hardware.components.others:*.name",
        ".hardware.components.others:*.serial",
        ".hardware.components.others:*.software",
        ".hardware.components.psus:",
        ".hardware.components.psus:*.description",
        ".hardware.components.psus:*.index",
        ".hardware.components.psus:*.location",
        ".hardware.components.psus:*.manufacturer",
        ".hardware.components.psus:*.model",
        ".hardware.components.psus:*.name",
        ".hardware.components.psus:*.serial",
        ".hardware.components.psus:*.software",
        ".hardware.components.sensors:",
        ".hardware.components.sensors:*.description",
        ".hardware.components.sensors:*.index",
        ".hardware.components.sensors:*.location",
        ".hardware.components.sensors:*.manufacturer",
        ".hardware.components.sensors:*.model",
        ".hardware.components.sensors:*.name",
        ".hardware.components.sensors:*.serial",
        ".hardware.components.sensors:*.software",
        ".hardware.components.stacks:",
        ".hardware.components.stacks:*.description",
        ".hardware.components.stacks:*.index",
        ".hardware.components.stacks:*.location",
        ".hardware.components.stacks:*.manufacturer",
        ".hardware.components.stacks:*.model",
        ".hardware.components.stacks:*.name",
        ".hardware.components.stacks:*.serial",
        ".hardware.components.stacks:*.software",
        ".hardware.components.unknowns:",
        ".hardware.components.unknowns:*.description",
        ".hardware.components.unknowns:*.index",
        ".hardware.components.unknowns:*.location",
        ".hardware.components.unknowns:*.manufacturer",
        ".hardware.components.unknowns:*.model",
        ".hardware.components.unknowns:*.name",
        ".hardware.components.unknowns:*.serial",
        ".hardware.components.unknowns:*.software",
        ".hardware.cpu.",
        ".hardware.cpu.arch",
        ".hardware.cpu.bus_speed",
        ".hardware.cpu.cache_size",
        ".hardware.cpu.cores",
        ".hardware.cpu.cores_per_cpu",
        ".hardware.cpu.cpu_max_capa",
        ".hardware.cpu.cpus",
        ".hardware.cpu.entitlement",
        ".hardware.cpu.implementation_mode",
        ".hardware.cpu.logical_cpus",
        ".hardware.cpu.max_speed",
        ".hardware.cpu.model",
        ".hardware.cpu.nodes:",
        ".hardware.cpu.nodes:*.cores",
        ".hardware.cpu.nodes:*.model",
        ".hardware.cpu.nodes:*.node_name",
        ".hardware.cpu.sharing_mode",
        ".hardware.cpu.smt_threads",
        ".hardware.cpu.threads",
        ".hardware.cpu.threads_per_cpu",
        ".hardware.cpu.type",
        ".hardware.cpu.voltage",
        ".hardware.firmware.",
        ".hardware.firmware.redfish:",
        ".hardware.firmware.redfish:*.component",
        ".hardware.firmware.redfish:*.description",
        ".hardware.firmware.redfish:*.location",
        ".hardware.firmware.redfish:*.updateable",
        ".hardware.firmware.redfish:*.version",
        ".hardware.memory.",
        ".hardware.memory.arrays:",
        ".hardware.memory.arrays:*.",
        ".hardware.memory.arrays:*.devices:",
        ".hardware.memory.arrays:*.devices:*.index",
        ".hardware.memory.arrays:*.devices:*.bank_locator",
        ".hardware.memory.arrays:*.devices:*.data_width",
        ".hardware.memory.arrays:*.devices:*.form_factor",
        ".hardware.memory.arrays:*.devices:*.locator",
        ".hardware.memory.arrays:*.devices:*.manufacturer",
        ".hardware.memory.arrays:*.devices:*.serial",
        ".hardware.memory.arrays:*.devices:*.size",
        ".hardware.memory.arrays:*.devices:*.speed",
        ".hardware.memory.arrays:*.devices:*.total_width",
        ".hardware.memory.arrays:*.devices:*.type",
        ".hardware.memory.arrays:*.maximum_capacity",
        ".hardware.memory.total_ram_usable",
        ".hardware.memory.total_swap",
        ".hardware.memory.total_vmalloc",
        ".hardware.nwadapter:",
        ".hardware.nwadapter:*.",
        ".hardware.nwadapter:*.gateway",
        ".hardware.nwadapter:*.ipv4_address",
        ".hardware.nwadapter:*.ipv4_subnet",
        ".hardware.nwadapter:*.ipv6_address",
        ".hardware.nwadapter:*.ipv6_subnet",
        ".hardware.nwadapter:*.macaddress",
        ".hardware.nwadapter:*.name",
        ".hardware.nwadapter:*.speed",
        ".hardware.nwadapter:*.type",
        ".hardware.storage.",
        ".hardware.storage.controller.",
        ".hardware.storage.controller.version",
        ".hardware.storage.disks.size",
        ".hardware.storage.disks:",
        ".hardware.storage.disks:*.",
        ".hardware.storage.disks:*.bus",
        ".hardware.storage.disks:*.controller",
        ".hardware.storage.disks:*.drive_index",
        ".hardware.storage.disks:*.fsnode",
        ".hardware.storage.disks:*.local",
        ".hardware.storage.disks:*.product",
        ".hardware.storage.disks:*.serial",
        ".hardware.storage.disks:*.signature",
        ".hardware.storage.disks:*.size",
        ".hardware.storage.disks:*.type",
        ".hardware.storage.disks:*.vendor",
        ".hardware.system.",
        ".hardware.system.device_number",
        ".hardware.system.description",
        ".hardware.system.expresscode",
        ".hardware.system.mac_address",
        ".hardware.system.manufacturer",
        ".hardware.system.model",
        ".hardware.system.model_name",
        ".hardware.system.node_name",
        ".hardware.system.nodes:",
        ".hardware.system.nodes:*.id",
        ".hardware.system.nodes:*.model",
        ".hardware.system.nodes:*.node_name",
        ".hardware.system.nodes:*.product",
        ".hardware.system.nodes:*.serial",
        ".hardware.system.partition_name",
        ".hardware.system.pki_appliance_version",
        ".hardware.system.product",
        ".hardware.system.serial",
        ".hardware.system.serial_number",
        ".hardware.video:",
        ".hardware.video:*.",
        ".hardware.video:*.driver",
        ".hardware.video:*.driver_date",
        ".hardware.video:*.driver_version",
        ".hardware.video:*.graphic_memory",
        ".hardware.video:*.name",
        ".hardware.video:*.slot",
        ".hardware.video:*.subsystem",
        ".hardware.volumes.",
        ".hardware.volumes.physical_volumes:",
        ".hardware.volumes.physical_volumes:*.physical_volume_free_partitions",
        ".hardware.volumes.physical_volumes:*.physical_volume_name",
        ".hardware.volumes.physical_volumes:*.physical_volume_status",
        ".hardware.volumes.physical_volumes:*.physical_volume_total_partitions",
        ".hardware.volumes.physical_volumes:*.volume_group_name",
        ".networking.",
        ".networking.addresses:",
        ".networking.addresses:*.address",
        ".networking.addresses:*.device",
        ".networking.addresses:*.type",
        ".networking.available_ethernet_ports",
        ".networking.hostname",
        ".networking.interfaces:",
        ".networking.interfaces:*.admin_status",
        ".networking.interfaces:*.alias",
        ".networking.interfaces:*.available",
        ".networking.interfaces:*.description",
        ".networking.interfaces:*.index",
        ".networking.interfaces:*.last_change",
        ".networking.interfaces:*.oper_status",
        ".networking.interfaces:*.phys_address",
        ".networking.interfaces:*.port_type",
        ".networking.interfaces:*.speed",
        ".networking.interfaces:*.vlans",
        ".networking.interfaces:*.vlantype",
        ".networking.kube:",
        ".networking.kube:*.address_type",
        ".networking.kube:*.ip",
        ".networking.routes:",
        ".networking.routes:*.device",
        ".networking.routes:*.gateway",
        ".networking.routes:*.target",
        ".networking.routes:*.type",
        ".networking.total_ethernet_ports",
        ".networking.total_interfaces",
        ".networking.tunnels:",
        ".networking.tunnels:*.index",
        ".networking.tunnels:*.linkpriority",
        ".networking.tunnels:*.peerip",
        ".networking.tunnels:*.peername",
        ".networking.tunnels:*.sourceip",
        ".networking.tunnels:*.tunnelinterface",
        ".networking.wlan.",
        ".networking.wlan.controller.",
        ".networking.wlan.controller.accesspoints:",
        ".networking.wlan.controller.accesspoints:*.group",
        ".networking.wlan.controller.accesspoints:*.ip_addr",
        ".networking.wlan.controller.accesspoints:*.model",
        ".networking.wlan.controller.accesspoints:*.name",
        ".networking.wlan.controller.accesspoints:*.serial",
        ".networking.wlan.controller.accesspoints:*.sys_location",
        ".software.",
        ".software.applications.",
        ".software.applications.azure.",
        ".software.applications.azure.application_gateways.",
        ".software.applications.azure.application_gateways.rules.",
        ".software.applications.azure.application_gateways.rules.backends:",
        ".software.applications.azure.application_gateways.rules.backends:*.address_pool_name",
        ".software.applications.azure.application_gateways.rules.backends:*.application_gateway",
        ".software.applications.azure.application_gateways.rules.backends:*.port",
        ".software.applications.azure.application_gateways.rules.backends:*.protocol",
        ".software.applications.azure.application_gateways.rules.backends:*.rule",
        ".software.applications.azure.application_gateways.rules.listeners.private_ips:",
        ".software.applications.azure.application_gateways.rules.listeners.private_ips:*.allocation_method",
        ".software.applications.azure.application_gateways.rules.listeners.private_ips:*.application_gateway",
        ".software.applications.azure.application_gateways.rules.listeners.private_ips:*.ip_address",
        ".software.applications.azure.application_gateways.rules.listeners.private_ips:*.listener",
        ".software.applications.azure.application_gateways.rules.listeners.private_ips:*.rule",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.allocation_method",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.dns_fqdn",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.application_gateway",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.ip_address",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.listener",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.location",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.name",
        ".software.applications.azure.application_gateways.rules.listeners.public_ips:*.rule",
        ".software.applications.azure.application_gateways.rules.listeners:",
        ".software.applications.azure.application_gateways.rules.listeners:*.application_gateway",
        ".software.applications.azure.application_gateways.rules.listeners:*.host_names",
        ".software.applications.azure.application_gateways.rules.listeners:*.listener",
        ".software.applications.azure.application_gateways.rules.listeners:*.port",
        ".software.applications.azure.application_gateways.rules.listeners:*.protocol",
        ".software.applications.azure.application_gateways.rules.listeners:*.rule",
        ".software.applications.azure.load_balancers.",
        ".software.applications.azure.load_balancers.inbound_nat_rules.backend_ip_configs:",
        ".software.applications.azure.load_balancers.inbound_nat_rules.backend_ip_configs:*.backend_ip_config",
        ".software.applications.azure.load_balancers.inbound_nat_rules.backend_ip_configs:*.inbound_nat_rule",
        ".software.applications.azure.load_balancers.inbound_nat_rules.backend_ip_configs:*.ip_address",
        ".software.applications.azure.load_balancers.inbound_nat_rules.backend_ip_configs:*.ip_allocation_method",
        ".software.applications.azure.load_balancers.inbound_nat_rules.backend_ip_configs:*.load_balancer",
        ".software.applications.azure.load_balancers.inbound_nat_rules.private_ips:",
        ".software.applications.azure.load_balancers.inbound_nat_rules.private_ips:*.inbound_nat_rule",
        ".software.applications.azure.load_balancers.inbound_nat_rules.private_ips:*.ip_address",
        ".software.applications.azure.load_balancers.inbound_nat_rules.private_ips:*.ip_allocation_method",
        ".software.applications.azure.load_balancers.inbound_nat_rules.private_ips:*.load_balancer",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.dns_fqdn",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.inbound_nat_rule",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.ip_address",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.ip_allocation_method",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.load_balancer",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.location",
        ".software.applications.azure.load_balancers.inbound_nat_rules.public_ips:*.public_ip_name",
        ".software.applications.azure.load_balancers.inbound_nat_rules:",
        ".software.applications.azure.load_balancers.inbound_nat_rules:*.backend_port",
        ".software.applications.azure.load_balancers.inbound_nat_rules:*.frontend_port",
        ".software.applications.azure.load_balancers.inbound_nat_rules:*.inbound_nat_rule",
        ".software.applications.azure.load_balancers.inbound_nat_rules:*.load_balancer",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.address_name",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.backend_pool",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.ip_address",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.ip_allocation_method",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.load_balancer",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.outbound_rule",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools.addresses:*.primary",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools:",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools:*.backend_pool",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools:*.load_balancer",
        ".software.applications.azure.load_balancers.outbound_rules.backend_pools:*.outbound_rule",
        ".software.applications.azure.load_balancers.outbound_rules:",
        ".software.applications.azure.load_balancers.outbound_rules:*.idle_timeout",
        ".software.applications.azure.load_balancers.outbound_rules:*.load_balancer",
        ".software.applications.azure.load_balancers.outbound_rules:*.outbound_rule",
        ".software.applications.azure.load_balancers.outbound_rules:*.protocol",
        ".software.applications.check_mk.",
        ".software.applications.check_mk.cluster.",
        ".software.applications.check_mk.cluster.is_cluster",
        ".software.applications.check_mk.cluster.nodes:",
        ".software.applications.check_mk.cluster.nodes:*.name",
        ".software.applications.check_mk.num_hosts",
        ".software.applications.check_mk.num_services",
        ".software.applications.check_mk.sites:",
        ".software.applications.check_mk.sites:*.apache",
        ".software.applications.check_mk.sites:*.autostart",
        ".software.applications.check_mk.sites:*.check_helper_usage",
        ".software.applications.check_mk.sites:*.check_mk_helper_usage",
        ".software.applications.check_mk.sites:*.checker_helper_usage",
        ".software.applications.check_mk.sites:*.cmc",
        ".software.applications.check_mk.sites:*.crontab",
        ".software.applications.check_mk.sites:*.dcd",
        ".software.applications.check_mk.sites:*.fetcher_helper_usage",
        ".software.applications.check_mk.sites:*.liveproxyd",
        ".software.applications.check_mk.sites:*.livestatus_usage",
        ".software.applications.check_mk.sites:*.mkeventd",
        ".software.applications.check_mk.sites:*.mknotifyd",
        ".software.applications.check_mk.sites:*.nagios",
        ".software.applications.check_mk.sites:*.npcd",
        ".software.applications.check_mk.sites:*.num_hosts",
        ".software.applications.check_mk.sites:*.num_services",
        ".software.applications.check_mk.sites:*.rrdcached",
        ".software.applications.check_mk.sites:*.site",
        ".software.applications.check_mk.sites:*.stunnel",
        ".software.applications.check_mk.sites:*.used_version",
        ".software.applications.check_mk.sites:*.xinetd",
        ".software.applications.check_mk.versions:",
        ".software.applications.check_mk.versions:*.demo",
        ".software.applications.check_mk.versions:*.edition",
        ".software.applications.check_mk.versions:*.num_sites",
        ".software.applications.check_mk.versions:*.number",
        ".software.applications.check_mk.versions:*.version",
        ".software.applications.checkmk-agent.",
        ".software.applications.checkmk-agent.version",
        ".software.applications.checkmk-agent.agentdirectory",
        ".software.applications.checkmk-agent.datadirectory",
        ".software.applications.checkmk-agent.spooldirectory",
        ".software.applications.checkmk-agent.pluginsdirectory",
        ".software.applications.checkmk-agent.localdirectory",
        ".software.applications.checkmk-agent.agentcontroller",
        ".software.applications.checkmk-agent.local_checks:",
        ".software.applications.checkmk-agent.local_checks:*.cache_interval",
        ".software.applications.checkmk-agent.local_checks:*.name",
        ".software.applications.checkmk-agent.local_checks:*.version",
        ".software.applications.checkmk-agent.plugins:",
        ".software.applications.checkmk-agent.plugins:*.cache_interval",
        ".software.applications.checkmk-agent.plugins:*.name",
        ".software.applications.checkmk-agent.plugins:*.version",
        ".software.applications.citrix.",
        ".software.applications.citrix.controller.",
        ".software.applications.citrix.controller.controller_version",
        ".software.applications.citrix.vm.",
        ".software.applications.citrix.vm.agent_version",
        ".software.applications.citrix.vm.catalog",
        ".software.applications.citrix.vm.desktop_group_name",
        ".software.applications.docker.",
        ".software.applications.docker.container.",
        ".software.applications.docker.container.networks:",
        ".software.applications.docker.container.networks:*.gateway",
        ".software.applications.docker.container.networks:*.ip_address",
        ".software.applications.docker.container.networks:*.ip_prefixlen",
        ".software.applications.docker.container.networks:*.mac_address",
        ".software.applications.docker.container.networks:*.name",
        ".software.applications.docker.container.networks:*.network_id",
        ".software.applications.docker.container.node_name",
        ".software.applications.docker.container.ports:",
        ".software.applications.docker.container.ports:*.host_addresses",
        ".software.applications.docker.container.ports:*.port",
        ".software.applications.docker.container.ports:*.protocol",
        ".software.applications.docker.containers:",
        ".software.applications.docker.containers:*.creation",
        ".software.applications.docker.containers:*.id",
        ".software.applications.docker.containers:*.image",
        ".software.applications.docker.containers:*.labels",
        ".software.applications.docker.containers:*.name",
        ".software.applications.docker.containers:*.status",
        ".software.applications.docker.images:",
        ".software.applications.docker.images:*.amount_containers",
        ".software.applications.docker.images:*.creation",
        ".software.applications.docker.images:*.id",
        ".software.applications.docker.images:*.labels",
        ".software.applications.docker.images:*.repodigests",
        ".software.applications.docker.images:*.repotags",
        ".software.applications.docker.images:*.size",
        ".software.applications.docker.networks.containers:",
        ".software.applications.docker.networks.containers:*.id",
        ".software.applications.docker.networks.containers:*.ipv4_address",
        ".software.applications.docker.networks.containers:*.ipv6_address",
        ".software.applications.docker.networks.containers:*.mac_address",
        ".software.applications.docker.networks.containers:*.name",
        ".software.applications.docker.networks.containers:*.network_id",
        ".software.applications.docker.networks:",
        ".software.applications.docker.networks:*.labels",
        ".software.applications.docker.networks:*.name",
        ".software.applications.docker.networks:*.network_id",
        ".software.applications.docker.networks:*.scope",
        ".software.applications.docker.networks:*.short_id",
        ".software.applications.docker.node_labels:",
        ".software.applications.docker.node_labels:*.label",
        ".software.applications.docker.num_containers_paused",
        ".software.applications.docker.num_containers_running",
        ".software.applications.docker.num_containers_stopped",
        ".software.applications.docker.num_containers_total",
        ".software.applications.docker.num_images",
        ".software.applications.docker.registry",
        ".software.applications.docker.swarm_manager:",
        ".software.applications.docker.swarm_manager:*.Addr",
        ".software.applications.docker.swarm_manager:*.NodeID",
        ".software.applications.docker.swarm_node_id",
        ".software.applications.docker.swarm_state",
        ".software.applications.docker.version",
        ".software.applications.fortinet.",
        ".software.applications.fortinet.fortigate_high_availability.",
        ".software.applications.fortinet.fortisandbox:",
        ".software.applications.fortinet.fortisandbox:*.name",
        ".software.applications.fortinet.fortisandbox:*.version",
        ".software.applications.fritz.",
        ".software.applications.fritz.auto_disconnect_time",
        ".software.applications.fritz.dns_server_1",
        ".software.applications.fritz.dns_server_2",
        ".software.applications.fritz.link_type",
        ".software.applications.fritz.upnp_config_enabled",
        ".software.applications.fritz.voip_dns_server_1",
        ".software.applications.fritz.voip_dns_server_2",
        ".software.applications.fritz.wan_access_type",
        ".software.applications.ibm_mq.",
        ".software.applications.ibm_mq.channels",
        ".software.applications.ibm_mq.channels:",
        ".software.applications.ibm_mq.channels:*.monchl",
        ".software.applications.ibm_mq.channels:*.name",
        ".software.applications.ibm_mq.channels:*.qmgr",
        ".software.applications.ibm_mq.channels:*.status",
        ".software.applications.ibm_mq.channels:*.type",
        ".software.applications.ibm_mq.managers",
        ".software.applications.ibm_mq.managers:",
        ".software.applications.ibm_mq.managers:*.ha",
        ".software.applications.ibm_mq.managers:*.instname",
        ".software.applications.ibm_mq.managers:*.instver",
        ".software.applications.ibm_mq.managers:*.name",
        ".software.applications.ibm_mq.managers:*.standby",
        ".software.applications.ibm_mq.managers:*.status",
        ".software.applications.ibm_mq.queues",
        ".software.applications.ibm_mq.queues:",
        ".software.applications.ibm_mq.queues:*.altered",
        ".software.applications.ibm_mq.queues:*.created",
        ".software.applications.ibm_mq.queues:*.maxdepth",
        ".software.applications.ibm_mq.queues:*.maxmsgl",
        ".software.applications.ibm_mq.queues:*.monq",
        ".software.applications.ibm_mq.queues:*.name",
        ".software.applications.ibm_mq.queues:*.qmgr",
        ".software.applications.kube.",
        ".software.applications.kube.cluster.",
        ".software.applications.kube.cluster.version",
        ".software.applications.kube.containers:",
        ".software.applications.kube.containers:*.container_id",
        ".software.applications.kube.containers:*.image",
        ".software.applications.kube.containers:*.image_id",
        ".software.applications.kube.containers:*.image_pull_policy",
        ".software.applications.kube.containers:*.name",
        ".software.applications.kube.containers:*.ready",
        ".software.applications.kube.containers:*.restart_count",
        ".software.applications.kube.daemonset.",
        ".software.applications.kube.daemonset.match_expressions",
        ".software.applications.kube.daemonset.match_labels",
        ".software.applications.kube.daemonset.strategy",
        ".software.applications.kube.deployment.",
        ".software.applications.kube.deployment.match_expressions",
        ".software.applications.kube.deployment.match_labels",
        ".software.applications.kube.deployment.strategy",
        ".software.applications.kube.labels:",
        ".software.applications.kube.labels:*.label_name",
        ".software.applications.kube.labels:*.label_value",
        ".software.applications.kube.metadata.",
        ".software.applications.kube.metadata.name",
        ".software.applications.kube.metadata.namespace",
        ".software.applications.kube.metadata.object",
        ".software.applications.kube.node.",
        ".software.applications.kube.node.architecture",
        ".software.applications.kube.node.container_runtime_version",
        ".software.applications.kube.node.kernel_version",
        ".software.applications.kube.node.kube_proxy_version",
        ".software.applications.kube.node.kubelet_version",
        ".software.applications.kube.node.operating_system",
        ".software.applications.kube.node.os_image",
        ".software.applications.kube.pod.",
        ".software.applications.kube.pod.dns_policy",
        ".software.applications.kube.pod.host_ip",
        ".software.applications.kube.pod.host_network",
        ".software.applications.kube.pod.node",
        ".software.applications.kube.pod.pod_ip",
        ".software.applications.kube.pod.qos_class",
        ".software.applications.kube.statefulset.",
        ".software.applications.kube.statefulset.match_expressions",
        ".software.applications.kube.statefulset.match_labels",
        ".software.applications.kube.statefulset.strategy",
        ".software.applications.mobileiron.",
        ".software.applications.mobileiron.partition_name",
        ".software.applications.mobileiron.registration_state",
        ".software.applications.mssql.",
        ".software.applications.mssql.instances:",
        ".software.applications.mssql.instances:*.active_node",
        ".software.applications.mssql.instances:*.cluster_name",
        ".software.applications.mssql.instances:*.clustered",
        ".software.applications.mssql.instances:*.edition",
        ".software.applications.mssql.instances:*.name",
        ".software.applications.mssql.instances:*.node_names",
        ".software.applications.mssql.instances:*.product",
        ".software.applications.mssql.instances:*.version",
        ".software.applications.oracle.",
        ".software.applications.oracle.dataguard_stats:",
        ".software.applications.oracle.dataguard_stats:*.db_unique",
        ".software.applications.oracle.dataguard_stats:*.role",
        ".software.applications.oracle.dataguard_stats:*.sid",
        ".software.applications.oracle.dataguard_stats:*.switchover",
        ".software.applications.oracle.instance:",
        ".software.applications.oracle.instance:*.db_creation_time",
        ".software.applications.oracle.instance:*.db_uptime",
        ".software.applications.oracle.instance:*.logins",
        ".software.applications.oracle.instance:*.logmode",
        ".software.applications.oracle.instance:*.openmode",
        ".software.applications.oracle.instance:*.pname",
        ".software.applications.oracle.instance:*.sid",
        ".software.applications.oracle.instance:*.version",
        ".software.applications.oracle.pga:",
        ".software.applications.oracle.pga:*.aggregate_pga_auto_target",
        ".software.applications.oracle.pga:*.aggregate_pga_target_parameter",
        ".software.applications.oracle.pga:*.bytes_processed",
        ".software.applications.oracle.pga:*.extra_bytes_read_written",
        ".software.applications.oracle.pga:*.global_memory_bound",
        ".software.applications.oracle.pga:*.maximum_pga_allocated",
        ".software.applications.oracle.pga:*.maximum_pga_used_for_auto_workareas",
        ".software.applications.oracle.pga:*.maximum_pga_used_for_manual_workareas",
        ".software.applications.oracle.pga:*.sid",
        ".software.applications.oracle.pga:*.total_freeable_pga_memory",
        ".software.applications.oracle.pga:*.total_pga_allocated",
        ".software.applications.oracle.pga:*.total_pga_inuse",
        ".software.applications.oracle.pga:*.total_pga_used_for_auto_workareas",
        ".software.applications.oracle.pga:*.total_pga_used_for_manual_workareas",
        ".software.applications.oracle.recovery_area:",
        ".software.applications.oracle.recovery_area:*.flashback",
        ".software.applications.oracle.recovery_area:*.sid",
        ".software.applications.oracle.sga:",
        ".software.applications.oracle.sga:*.buf_cache_size",
        ".software.applications.oracle.sga:*.data_trans_cache_size",
        ".software.applications.oracle.sga:*.fixed_size",
        ".software.applications.oracle.sga:*.free_mem_avail",
        ".software.applications.oracle.sga:*.granule_size",
        ".software.applications.oracle.sga:*.in_mem_area_size",
        ".software.applications.oracle.sga:*.java_pool_size",
        ".software.applications.oracle.sga:*.large_pool_size",
        ".software.applications.oracle.sga:*.max_size",
        ".software.applications.oracle.sga:*.redo_buffer",
        ".software.applications.oracle.sga:*.shared_io_pool_size",
        ".software.applications.oracle.sga:*.shared_pool_size",
        ".software.applications.oracle.sga:*.sid",
        ".software.applications.oracle.sga:*.start_oh_shared_pool",
        ".software.applications.oracle.sga:*.streams_pool_size",
        ".software.applications.oracle.systemparameter:",
        ".software.applications.oracle.systemparameter:*.isdefault",
        ".software.applications.oracle.systemparameter:*.name",
        ".software.applications.oracle.systemparameter:*.sid",
        ".software.applications.oracle.systemparameter:*.value",
        ".software.applications.oracle.tablespaces:",
        ".software.applications.oracle.tablespaces:*.autoextensible",
        ".software.applications.oracle.tablespaces:*.current_size",
        ".software.applications.oracle.tablespaces:*.free_space",
        ".software.applications.oracle.tablespaces:*.increment_size",
        ".software.applications.oracle.tablespaces:*.max_size",
        ".software.applications.oracle.tablespaces:*.name",
        ".software.applications.oracle.tablespaces:*.num_increments",
        ".software.applications.oracle.tablespaces:*.sid",
        ".software.applications.oracle.tablespaces:*.type",
        ".software.applications.oracle.tablespaces:*.used_size",
        ".software.applications.oracle.tablespaces:*.version",
        ".software.applications.synthetic_monitoring.",
        ".software.applications.synthetic_monitoring.plans:",
        ".software.applications.synthetic_monitoring.plans:*.application",
        ".software.applications.synthetic_monitoring.plans:*.suite_name",
        ".software.applications.synthetic_monitoring.plans:*.plan_id",
        ".software.applications.synthetic_monitoring.plans:*.variant",
        ".software.applications.synthetic_monitoring.tests:",
        ".software.applications.synthetic_monitoring.tests:*.application",
        ".software.applications.synthetic_monitoring.tests:*.bottom_level_suite_name",
        ".software.applications.synthetic_monitoring.tests:*.plan_id",
        ".software.applications.synthetic_monitoring.tests:*.suite_name",
        ".software.applications.synthetic_monitoring.tests:*.test_name",
        ".software.applications.synthetic_monitoring.tests:*.test_item",
        ".software.applications.synthetic_monitoring.tests:*.top_level_suite_name",
        ".software.applications.synthetic_monitoring.tests:*.variant",
        ".software.applications.vmwareesx.",
        ".software.applications.vmwareesx:*.",
        ".software.applications.vmwareesx:*.clusters.",
        ".software.applications.vmwareesx:*.clusters:*.",
        ".software.bios.",
        ".software.bios.date",
        ".software.bios.vendor",
        ".software.bios.version",
        ".software.configuration.",
        ".software.configuration.organisation.",
        ".software.configuration.organisation.address",
        ".software.configuration.organisation.network_id",
        ".software.configuration.organisation.organisation_id",
        ".software.configuration.organisation.organisation_name",
        ".software.configuration.snmp_info.",
        ".software.configuration.snmp_info.contact",
        ".software.configuration.snmp_info.location",
        ".software.configuration.snmp_info.name",
        ".software.firmware.",
        ".software.firmware.platform_level",
        ".software.firmware.vendor",
        ".software.firmware.version",
        ".software.kernel_config:",
        ".software.kernel_config:*.name",
        ".software.kernel_config:*.value",
        ".software.os.",
        ".software.os.arch",
        ".software.os.build",
        ".software.os.install_date",
        ".software.os.kernel_version",
        ".software.os.name",
        ".software.os.service_pack",
        ".software.os.service_packs:",
        ".software.os.service_packs:*.name",
        ".software.os.type",
        ".software.os.vendor",
        ".software.os.version",
        ".software.packages:",
        ".software.packages:*.arch",
        ".software.packages:*.install_date",
        ".software.packages:*.name",
        ".software.packages:*.package_type",
        ".software.packages:*.package_version",
        ".software.packages:*.path",
        ".software.packages:*.size",
        ".software.packages:*.summary",
        ".software.packages:*.vendor",
        ".software.packages:*.version",
    ]

    assert set(inventory_displayhints) == set(expected)


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
