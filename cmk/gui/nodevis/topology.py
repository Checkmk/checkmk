#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import abc
import glob
import json
import os
import re
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal, override

import livestatus

import cmk.ccc.plugin_registry
import cmk.gui.visuals
import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.ccc.store import locked
from cmk.ccc.user import UserId
from cmk.gui import sites
from cmk.gui.breadcrumb import make_current_page_breadcrumb_item, make_topic_breadcrumb
from cmk.gui.config import Config
from cmk.gui.cron import CronJob, CronJobRegistry
from cmk.gui.dashboard import get_topology_context_and_filters
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.log import logger
from cmk.gui.logged_in import user
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.nodevis import frontend_texts
from cmk.gui.nodevis.filters import FilterTopologyMaxNodes, FilterTopologyMeshDepth
from cmk.gui.nodevis.type_defs import (
    FrontendConfiguration,
    GrowthSettings,
    HierarchyNode,
    Layout,
    MKGrowthExceeded,
    MKGrowthInterruption,
    NodeConfig,
    NodeType,
    OverlaysConfig,
    TopologyConfiguration,
    TopologyFilterConfiguration,
    TopologyLink,
    TopologyLinkType,
    TopologyNode,
    TopologyNodes,
    TopologyQueryIdentifier,
    TopologyResponse,
)
from cmk.gui.nodevis.utils import (
    CoreDataProvider,
    get_compare_history_page_menu_entry,
    get_toggle_layout_designer_page_menu_entry,
    topology_configs_dir,
    topology_data_dir,
    topology_settings_lookup,
)
from cmk.gui.page_menu import (
    make_display_options_dropdown,
    PageMenu,
    PageMenuEntry,
    PageMenuSidePopup,
    PageMenuTopic,
)
from cmk.gui.pages import AjaxPage, Page, PageContext, PageEndpoint, PageRegistry, PageResult
from cmk.gui.pagetypes import PagetypeTopics
from cmk.gui.permissions import permission_registry
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import (
    ColumnSpec,
    DynamicIcon,
    DynamicIconName,
    IconNames,
    PainterParameters,
    Row,
    StaticIcon,
    Visual,
    VisualLinkSpec,
)
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.views.icon import Icon, IconConfig, IconRegistry
from cmk.gui.views.page_ajax_filters import ABCAjaxInitialFilters
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals import get_livestatus_filter_headers
from cmk.gui.visuals.filter import FilterRegistry
from cmk.utils.tags import TagID


@request_memoize()
def _core_data_provider() -> CoreDataProvider:
    return CoreDataProvider()


def register(
    page_registry: PageRegistry,
    filter_registry: FilterRegistry,
    icon_and_action_registry: IconRegistry,
    cron_job_registry: CronJobRegistry,
) -> None:
    page_registry.register(PageEndpoint("parent_child_topology", ParentChildTopologyPage()))
    page_registry.register(PageEndpoint("network_topology", NetworkTopologyPage()))
    page_registry.register(
        PageEndpoint("ajax_initial_topology_filters", AjaxInitialTopologyFilters())
    )
    page_registry.register(PageEndpoint("ajax_fetch_topology", AjaxFetchTopology()))
    icon_and_action_registry.register(NetworkTopologyIcon)
    cron_job_registry.register(
        CronJob(
            name="cleanup_topology_layouts",
            callable=cleanup_topology_layouts,
            interval=timedelta(days=1),
        )
    )
    filter_registry.register(FilterTopologyMeshDepth())
    filter_registry.register(FilterTopologyMaxNodes())
    topology_layer_registry.register(ParentChildDataGenerator)
    topology_layer_registry.register(GenericNetworkDataGenerator)
    _register_builtin_views()


def _render_network_topology_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
    icon_config: IconConfig,
) -> tuple[StaticIcon | DynamicIcon, str, str] | None:
    # Only show this icon if topology data is available
    files = glob.glob("data_*.json", root_dir=topology_data_dir / "default")
    if not files:
        return None

    url = makeuri_contextless(
        request,
        [("host_regex", f"{row['host_name']}$")],
        filename="network_topology.py",
    )
    return StaticIcon(IconNames.aggr), _("Network topology"), url


NetworkTopologyIcon = Icon(
    ident="network_topology",
    title=_l("Network topology"),
    host_columns=["name"],
    sort_index=51,
    render=_render_network_topology_icon,
)


def _delete_topology_configuration(
    topology_configuration: TopologyConfiguration,
) -> None:
    query_identifier = TopologyQueryIdentifier(
        topology_configuration.type, topology_configuration.filter
    )
    if not topology_settings_lookup.exists():
        return

    try:
        data = store.try_load_file_from_pickle_cache(
            topology_settings_lookup,
            default={},
            temp_dir=cmk.utils.paths.tmp_dir,
            root_dir=cmk.utils.paths.omd_root,
        )
    except json.JSONDecodeError:
        data = {}

    data.pop(hash(query_identifier), None)
    store.save_object_to_file(topology_settings_lookup, data)
    Path(_layout_path(str(hash(query_identifier)))).unlink(missing_ok=True)


def _save_topology_configuration(topology_configuration: TopologyConfiguration) -> None:
    query_identifier = TopologyQueryIdentifier(
        topology_configuration.type, topology_configuration.filter
    )
    if not topology_settings_lookup.exists():
        topology_configs_dir.mkdir(parents=True, exist_ok=True)
        topology_settings_lookup.touch()

    try:
        data = store.try_load_file_from_pickle_cache(
            topology_settings_lookup,
            default={},
            temp_dir=cmk.utils.paths.tmp_dir,
            root_dir=cmk.utils.paths.omd_root,
        )
    except json.JSONDecodeError:
        data = {}

    topology_hash = str(hash(query_identifier))
    data[query_identifier.identifier] = topology_hash

    # Note: Since the lookup uses tuple[str, ...] as keys we cannot store it as json
    store.save_object_to_file(topology_settings_lookup, data)

    # The actual settings are stored in a separate file
    config = asdict(topology_configuration)

    # We do NOT store the datasource configuration and available_layers
    # because these elements are not part of the fixed configuration
    config["frontend"].pop("datasource_configuration", None)
    config["frontend"]["overlays_config"].pop("available_layers", None)
    store.save_text_to_file(_layout_path(topology_hash), json.dumps(config))


class ABCTopologyPage(Page):
    _instance_name = "node_instance"

    @classmethod
    @abc.abstractmethod
    def visual_spec(cls) -> Visual:
        raise NotImplementedError

    @override
    def page(self, ctx: PageContext) -> None:
        """Determines the hosts to be shown"""
        user.need_permission("general.parent_child_topology")
        self.show_topology(UserPermissions.from_config(ctx.config, permission_registry))

    def show_topology(self, user_permissions: UserPermissions) -> None:
        visual_spec = self.visual_spec()
        breadcrumb = make_topic_breadcrumb(
            main_menu_registry.menu_monitoring(),
            PagetypeTopics.get_topic(visual_spec["topic"], user_permissions).title(),
        )
        breadcrumb.append(make_current_page_breadcrumb_item(str(visual_spec["title"])))
        page_menu = PageMenu(breadcrumb=breadcrumb)
        self._extend_display_dropdown(page_menu, visual_spec["name"])
        make_header(html, str(visual_spec["title"]), breadcrumb, page_menu)
        self.show_topology_content()

    def show_topology_content(self) -> None:
        div_id = "node_visualization"
        html.div("", id_=div_id)
        topology_configuration = get_topology_configuration(
            self.visual_spec()["name"], self.get_default_overlays_config()
        )
        result = _compute_topology_response(topology_configuration)
        html.javascript(
            f"{self._instance_name} = new cmk.nodevis.TopologyVisualization({json.dumps(div_id)},"
            f"{json.dumps(topology_configuration.type)},"
            f"{json.dumps(frontend_texts.get_texts())}"
            f");"
        )

        html.javascript(f"{self._instance_name}.show_topology({json.dumps(result)})")

    @classmethod
    @abc.abstractmethod
    def get_default_overlays_config(cls) -> OverlaysConfig:
        pass

    def _extend_display_dropdown(self, menu: PageMenu, page_name: str) -> None:
        context, _show_filters = get_topology_context_and_filters()
        display_dropdown = menu.get_dropdown_by_name("display", make_display_options_dropdown())

        display_dropdown.topics.insert(
            0,
            PageMenuTopic(
                title=_("Configuration"),
                entries=[
                    PageMenuEntry(
                        title=_("Filter"),
                        icon_name=StaticIcon(IconNames.filter),
                        item=PageMenuSidePopup(
                            cmk.gui.visuals.render_filter_form(
                                info_list=["host", "service"],
                                context=context,
                                page_name=page_name,
                                reset_ajax_page="ajax_initial_topology_filters",
                            )
                        ),
                        name="filters",
                        is_shortcut=True,
                    ),
                    *self._get_page_menu_entries(),
                ],
            ),
        )

    @classmethod
    @abc.abstractmethod
    def _get_page_menu_entries(cls) -> list[PageMenuEntry]:
        pass


class ParentChildTopologyPage(ABCTopologyPage):
    @classmethod
    def visual_spec(cls) -> Visual:
        return {
            "owner": UserId.builtin(),
            "description": "",
            "hidebutton": False,
            "public": True,
            "topic": "overview",
            "title": _("Parent / Child topology"),
            "name": "parent_child_topology",
            "sort_index": 50,
            "is_show_more": False,
            "icon": DynamicIconName("network_topology"),
            "hidden": False,
            "single_infos": [],
            "context": {},
            "link_from": {},
            "add_context_to_title": True,
            "packaged": False,
            "main_menu_search_terms": [],
        }

    @classmethod
    def get_default_overlays_config(cls) -> OverlaysConfig:
        return OverlaysConfig(
            available_layers=[ParentChildDataGenerator.ident],
            overlays={
                ParentChildDataGenerator.ident: {
                    "active": True,
                    "hidden": True,
                }
            },
        )

    @classmethod
    def _get_page_menu_entries(cls) -> list[PageMenuEntry]:
        return [
            get_toggle_layout_designer_page_menu_entry(),
        ]


class NetworkTopologyPage(ABCTopologyPage):
    @classmethod
    def visual_spec(cls) -> Visual:
        return {
            "owner": UserId.builtin(),
            "description": "",
            "hidebutton": False,
            "public": True,
            "topic": "overview",
            "title": _("Network topology"),
            "name": "network_topology",
            "sort_index": 50,
            "is_show_more": False,
            "icon": DynamicIconName("network_topology"),
            "hidden": False,
            "single_infos": [],
            "context": {},
            "link_from": {},
            "add_context_to_title": True,
            "packaged": False,
            "main_menu_search_terms": [],
        }

    @classmethod
    def get_default_overlays_config(cls) -> OverlaysConfig:
        layer_ids = _get_dynamic_layer_ids()
        return OverlaysConfig(
            available_layers=layer_ids,
            overlays={x: {"active": True} for x in layer_ids},
        )

    @classmethod
    def _get_page_menu_entries(cls) -> list[PageMenuEntry]:
        return [
            get_toggle_layout_designer_page_menu_entry(),
            get_compare_history_page_menu_entry(),
        ]


class AjaxInitialTopologyFilters(ABCAjaxInitialFilters):
    def _get_context(self, page_name: str) -> dict:
        _view, show_filters = get_topology_context_and_filters()
        return {f.ident: {} for f in show_filters if f.available()}


class AjaxFetchTopology(AjaxPage):
    @override
    def page(self, ctx: PageContext) -> PageResult:
        topology_type = request.get_str_input_mandatory("topology_type")
        if topology_type == "network_topology":
            default_overlays = NetworkTopologyPage.get_default_overlays_config()
        else:
            default_overlays = ParentChildTopologyPage.get_default_overlays_config()
        topology_configuration = get_topology_configuration(topology_type, default_overlays)
        if request.has_var("delete_topology_configuration"):
            _delete_topology_configuration(topology_configuration)
            topology_configuration.layout = _get_default_layout()
        if request.has_var("save_topology_configuration"):
            _save_topology_configuration(topology_configuration)

        try:
            return _compute_topology_response(topology_configuration)
        except Exception as e:
            logger.warning("".join(traceback.format_exception(e)))
        return None


class ABCTopologyNodeDataGenerator:
    ident = "abstract_ident"

    def __init__(
        self,
        root_hostnames_from_core: set[str],
        topology_configuration: TopologyConfiguration,
        data_folder: Path,
        add_data_root_node: bool = True,
    ):
        self._link_metadata: dict[tuple[str, str], Any] = {}
        self._topology_configuration = topology_configuration
        self._root_hostnames_from_core = root_hostnames_from_core
        self._data_folder = data_folder
        self._current_mesh_depth = 0
        self._topology_nodes: TopologyNodes = {}
        self._errors: list[str] = []
        self._add_data_root_node = add_data_root_node
        self._generate_data()

    @abc.abstractmethod
    def unique_id(self) -> str:
        pass

    @property
    def link_metadata(self) -> dict[tuple[str, str], Any]:
        return self._link_metadata

    @abc.abstractmethod
    def name(self) -> str:
        pass

    def get_topology_result(self) -> TopologyNodes:
        return self._topology_nodes

    def get_node_specific_info(self, _node: TopologyNode) -> dict[str, Any]:
        return {}

    def _add_error(self, error: str) -> None:
        self._errors.append(error)

    def _generate_data(
        self,
    ) -> None:
        root_nodes = self._topology_configuration.frontend.growth_root_nodes_set.union(
            self._root_hostnames_from_core
        )
        try:
            self._create_mesh(root_nodes)
        except MKGrowthExceeded as e:
            # Unexpected interuption, unable to display all nodes
            self._add_error(str(e))
        except MKGrowthInterruption:
            # Valid interruption, since the growth should stop when a given number of nodes is exceeded
            pass

        self._postprocess_mesh()

    def _create_mesh(self, root_nodes: set[str]) -> None:
        border_nodes = self._grow_to_mesh_depth(root_nodes)
        self._grow_continue_nodes(border_nodes)

    def _grow_to_mesh_depth(self, border_nodes: set[str]) -> set[str]:
        previous_border_nodes = set()

        while self._current_mesh_depth <= self._topology_configuration.filter.mesh_depth:
            previous_border_nodes = border_nodes
            border_nodes = self._process_nodes(border_nodes)
            self._check_mesh_size()
            self._current_mesh_depth += 1
        return previous_border_nodes

    def _grow_continue_nodes(self, border_nodes: set[str]) -> None:
        growth_continue_nodes = set(self._topology_configuration.frontend.growth_continue_nodes)
        while growth_continue_nodes:
            adjacent_nodes = set()
            for node_id in list(growth_continue_nodes):
                if node_id in self._topology_nodes:
                    adjacent_nodes.update(self._topology_nodes[node_id].outgoing)
                    adjacent_nodes.update(self._topology_nodes[node_id].incoming)
                    growth_continue_nodes.remove(node_id)
            growth_nodes = adjacent_nodes - set(self._topology_nodes.keys())
            if not growth_nodes:
                break
            self._process_nodes(growth_nodes)

    def _process_nodes(self, border_nodes: set[str]) -> set[str]:
        unknown_border_nodes = border_nodes - set(self._topology_nodes.keys())
        return self._update_meshes(self._fetch_data(unknown_border_nodes))

    @abc.abstractmethod
    def _fetch_data(self, node_ids: set[str]) -> TopologyNodes:
        pass

    def _update_meshes(self, nodes: TopologyNodes) -> set[str]:
        self._topology_nodes.update(nodes)

        all_border_nodes = set()
        for node_id, node in nodes.items():
            node.mesh_depth = self._current_mesh_depth
            if not self.growth_forbidden(node_id):
                border_nodes = {
                    x for x in node.outgoing.union(node.incoming) if x not in self._topology_nodes
                }
                all_border_nodes.update(border_nodes)
        return all_border_nodes

    def growth_forbidden(self, node_id: str) -> bool:
        return node_id in self._topology_configuration.frontend.growth_forbidden_nodes

    def _check_mesh_size(self) -> None:
        total_nodes = len(self._topology_nodes)
        if total_nodes > self._topology_configuration.filter.max_nodes:
            raise MKGrowthExceeded(
                _("Maximum number of nodes exceeded %d/%d")
                % (total_nodes, self._topology_configuration.filter.max_nodes)
            )
        if total_nodes > self._topology_configuration.filter.growth_auto_max_nodes:
            raise MKGrowthInterruption(
                _("Growth interrupted %d/%d")
                % (
                    total_nodes,
                    self._topology_configuration.filter.growth_auto_max_nodes,
                )
            )

    @abc.abstractmethod
    def _postprocess_mesh(self) -> None:
        pass


class ParentChildDataGenerator(ABCTopologyNodeDataGenerator):
    ident = "parent_child"
    _node_extra_info: dict[str, Any] = {}

    def unique_id(self) -> str:
        return "parent_child"

    def name(self) -> str:
        return _("Parent / Child")

    def get_node_specific_info(self, node: TopologyNode) -> dict[str, Any]:
        extra_info = self._node_extra_info.get(node.id)
        if extra_info is None:
            return {}
        result = {
            "core": {
                "hostname": extra_info["hostname"],
                "state": self._map_host_state(node, extra_info),
            }
        }
        if icon := extra_info.get("icon"):
            result["core"]["icon"] = theme.detect_icon_path(icon, "icon_")
        return result

    def _map_host_state(self, node: TopologyNode, extra_info: dict[str, Any]) -> int:
        if node.type in (NodeType.TOPOLOGY_CENTER, NodeType.TOPOLOGY_SITE):
            return 0
        if not extra_info["has_been_checked"]:
            return -1
        state_map = {
            0: 0,
            1: 2,
            2: 3,
        }
        return state_map.get(extra_info["state"], 3)

    def _create_mesh(self, root_nodes: set[str]) -> None:
        mesh_depth_border_nodes = self._grow_to_mesh_depth(root_nodes)
        parent_border_nodes = self._growth_to_parents()
        self._grow_continue_nodes(mesh_depth_border_nodes.union(parent_border_nodes))

    def _growth_to_parents(self) -> set[str]:
        maximum_depth = 100
        parent_border_nodes: set[str] = set()
        for _i in range(maximum_depth):
            all_parents: set[str] = set()
            for node in self._topology_nodes.values():
                all_parents.update(node.outgoing)

            missing_parents = all_parents - set(self._topology_nodes.keys())
            if not missing_parents:
                break
            parent_border_nodes.update(self._process_nodes(missing_parents))
        return parent_border_nodes

    def _fetch_data(self, node_ids: set[str]) -> TopologyNodes:
        response: TopologyNodes = {}
        hostname_filters = []
        if not node_ids:
            return response

        # If the host filter is going to be too large, simply query all hosts and do the
        # filtering afterward. This reduces the load on the core.
        # The amount of returned data is negligible
        query_all_hosts = len(node_ids) > 500
        if not query_all_hosts:
            for hostname in node_ids:
                hostname_filters.append("Filter: host_name = %s" % livestatus.lqencode(hostname))
            hostname_filters.append("Or: %d" % len(node_ids))

        with sites.prepend_site(), sites.set_limit(self._topology_configuration.filter.max_nodes):
            columns = [
                "name",
                "state",
                "alias",
                "icon_image",
                "parents",
                "childs",
                "has_been_checked",
            ]
            query_result = sites.live().query(
                "GET hosts\nColumns: {}\n{}".format(" ".join(columns), "\n".join(hostname_filters))
            )

        headers = ["site"] + columns
        core_info = [dict(zip(headers, x)) for x in query_result]
        for entry in core_info:
            if entry["name"] in self._topology_nodes:
                # Node already known
                continue

            if query_all_hosts and entry["name"] not in node_ids:
                continue

            self._node_extra_info[entry["name"]] = {
                "site": entry["site"],
                "hostname": entry["name"],
                "icon": entry["icon_image"],
                "state": entry["state"],
                "has_been_checked": entry["has_been_checked"],
            }
            response[entry["name"]] = TopologyNode(
                id=entry["name"],
                name=entry["name"],
                incoming=set(entry["childs"]),
                outgoing=set(entry["parents"]),
            )
        return response

    def _postprocess_mesh(self) -> None:
        """The depth of parent/child nodes is specified by the parent/child relationship,
        instead of the growth depth"""
        # Compute depth
        # Site Nodes - depth 0
        # Actual hosts - depth 1+
        nodes_to_compute = dict(self._topology_nodes.items())
        updated_nodes = set()

        # Cycle through nodes. Start: Find nodes without parents
        # Repeat until no nodes left: Find children for current parent -> repeat step
        for i in range(1, 1000):
            updated_at_depth = set()
            if not nodes_to_compute:
                break
            for node_id, node in list(nodes_to_compute.items()):
                at_depth = not node.outgoing
                for parent_id in node.outgoing:
                    if parent_id in updated_nodes:
                        at_depth = True
                        break
                if at_depth:
                    node.mesh_depth = i
                    nodes_to_compute.pop(node_id)
                    updated_at_depth.add(node_id)

            if not updated_at_depth:
                # Empty run. There still might be circular dependencies
                # which can't be resolved with this mechanism
                # The depth of the remaining nodes will be computed differently
                break
            updated_nodes.update(updated_at_depth)

        _resolve_circular_mesh_depths([], nodes_to_compute)

        def topo_site_id(site: str) -> str:
            return f"site:{site}"

        # Create site nodes
        for node_id, node in list(self._topology_nodes.items()):
            site_id = self._node_extra_info[node_id]["site"]
            internal_site_id = topo_site_id(site_id)
            if internal_site_id in self._topology_nodes:
                continue
            self._topology_nodes[internal_site_id] = TopologyNode(
                id=internal_site_id,
                name=_("Site %s") % site_id,
                mesh_depth=0,
                type=NodeType.TOPOLOGY_SITE,
            )

        # Link nodes with depth 1(no parents) to site
        for node_id, node in self._topology_nodes.items():
            if node.mesh_depth == 1:
                internal_site_id = topo_site_id(self._node_extra_info[node_id]["site"])
                self._topology_nodes[internal_site_id].outgoing.add(node_id)


@dataclass
class NetworkDataLookup:
    id: dict[str, Any] = field(default_factory=dict)
    hostname: dict[str, Any] = field(default_factory=dict)
    service: dict[str, dict[str, Any]] = field(default_factory=dict)
    connections_by_id: dict[str, list] = field(default_factory=dict)

    def translate_hostnames_to_network_id(self, hostnames: set[HostName]) -> set[str]:
        return {self.hostname[x] for x in hostnames if x in self.hostname}

    def core_entity_for_id(self, node_id: str) -> HostName | tuple[HostName, str] | None:
        value = self.id.get(node_id, {}).get("link", {}).get("core")
        if value is None:
            return value
        if isinstance(value, str):
            return HostName(value)
        return HostName(value[0]), value[1]


def _get_network_data(folder: Path, data_type: str) -> NetworkDataLookup:
    data_file = folder / f"data_{data_type}.json"
    if not data_file.exists():
        return NetworkDataLookup()
    parsed_file = folder / f"parsed_{data_type}"
    if parsed_file.exists() and parsed_file.stat().st_mtime > data_file.stat().st_mtime:
        return NetworkDataLookup(**json.loads(parsed_file.read_text()))

    parsed_data = _create_parsed_data(folder, data_type)
    store.save_text_to_file(parsed_file, json.dumps(asdict(parsed_data)))
    return parsed_data


def _create_parsed_data(folder: Path, data_type: str) -> NetworkDataLookup:
    """Create a quick host/service/id lookup out of the objects* and connections* files"""
    parsed_data = NetworkDataLookup()
    data_file = folder / f"data_{data_type}.json"
    if not data_file.exists():
        return parsed_data
    data = json.loads(data_file.read_text())
    for object_id, settings in data["objects"].items():
        parsed_data.id[object_id] = settings
        link_value: str | list[str]
        if link_value := settings["link"].get("core"):
            if isinstance(link_value, list):
                parsed_data.service.setdefault(link_value[0], {})[link_value[1]] = object_id
            else:
                parsed_data.hostname[link_value] = object_id

    for connection in data["connections"]:
        (source, target), _metadata = connection
        parsed_data.connections_by_id.setdefault(source, []).append(connection)
        parsed_data.connections_by_id.setdefault(target, []).append(connection)

    return parsed_data


class GenericNetworkDataGenerator(ABCTopologyNodeDataGenerator):
    ident = "network"
    _node_extra_info: dict[str, Any] = {}

    def __init__(
        self,
        data_type: str,
        root_hostnames_from_core: set[HostName],
        topology_configuration: TopologyConfiguration,
        data_folder: Path,
        add_data_root_node: bool,
    ):
        self._data_type = data_type
        self._network_data = _get_network_data(data_folder, data_type)
        # Translate hostnames core to network data ids
        network_data_ids = self._network_data.translate_hostnames_to_network_id(
            root_hostnames_from_core
        )
        super().__init__(network_data_ids, topology_configuration, data_folder, add_data_root_node)

    def unique_id(self) -> str:
        return _dynamic_network_data_id(self._data_type)

    def name(self) -> str:
        return self._data_type.title()

    def get_node_specific_info(self, node: TopologyNode) -> dict[str, Any]:
        extra_info = self._node_extra_info.get(node.id)
        result: dict[str, Any] = {}
        if extra_info:
            core_values = {}
            for what in (
                "service",
                "hostname",
                "state",
                "num_services_warn",
                "num_services_crit",
            ):
                if (value := extra_info.get(what)) is not None:
                    core_values[what] = value
            if "state" in core_values and "service" not in core_values:
                core_values["state"] = self._map_host_state(node, extra_info)

            if icon := extra_info.get("icon"):
                core_values["icon"] = icon
            result["core"] = core_values

        image_metadata = node.metadata.get("images", {})
        for icon_type in ("icon", "emblem"):
            if icon := image_metadata.get(icon_type):
                result.setdefault("node_images", {})[icon_type] = theme.detect_icon_path(icon, "")

        if tooltip := node.metadata.get("tooltip"):
            result["tooltip"] = tooltip

        if custom_settings := self._topology_configuration.frontend.custom_node_settings.get(
            node.id
        ):
            result["custom_node_settings"] = custom_settings
        return result

    def _map_host_state(self, node: TopologyNode, extra_info: dict[str, Any]) -> int:
        if node.type in (NodeType.TOPOLOGY_CENTER, NodeType.TOPOLOGY_SITE):
            return 0
        if not extra_info["has_been_checked"]:
            return -1
        state_map = {
            0: 0,
            2: 3,
        }
        return state_map.get(extra_info["state"], 3)

    def _store_link_metadata(
        self, source_id: str, target_id: str, metadata: dict[str, Any]
    ) -> None:
        self._link_metadata.setdefault((source_id, target_id), {}).update(metadata)

    def _fetch_data(self, node_ids: set[str]) -> TopologyNodes:
        response: TopologyNodes = {}
        for node_id in node_ids:
            if network_object := self._network_data.id.get(node_id):
                topology_node = TopologyNode(
                    id=node_id,
                    name=network_object.get("name", node_id),
                    metadata=network_object.get("metadata", {}),
                )
                for (
                    source,
                    target,
                ), metadata in self._network_data.connections_by_id.get(node_id, []):
                    if source == node_id:
                        topology_node.outgoing.add(target)
                    else:
                        topology_node.incoming.add(source)
                    self._store_link_metadata(source, target, metadata)
                response[node_id] = topology_node
        return response

    def _postprocess_mesh(self) -> None:
        if not self._topology_nodes:
            return

        self._enrich_nodes_with_core_data()
        self._apply_service_visibility()

        start_node_ids = sorted((x for x, y in self._topology_nodes.items() if y.mesh_depth == 0))
        _resolve_circular_mesh_depths(
            list(self._topology_nodes[x] for x in start_node_ids), self._topology_nodes
        )

        if self._add_data_root_node:
            # Add root node for all nodes in this datasource. Useful when having multiple datasources
            root_node = f"datatype_root#{self._data_type}"
            self._topology_nodes[root_node] = TopologyNode(
                id=root_node,
                name=self._data_type,
                mesh_depth=0,
                type=NodeType.TOPOLOGY_SITE,
                incoming={x for x, y in self._topology_nodes.items() if y.mesh_depth == 1},
            )
        else:
            # Shift all nodes towards toplevel
            for node in self._topology_nodes.values():
                node.mesh_depth = node.mesh_depth - 1

    def _apply_service_visibility(self) -> None:
        general_service_visibility = (
            self._topology_configuration.frontend.overlays_config.computation_options.show_services
        )

        def remove_service(remove_node: TopologyNode) -> None:
            # Create links between adjacent objects and remove node from topology_nodes
            all_ids = remove_node.outgoing.union(remove_node.incoming)
            adjacent_node_ids = sorted(x for x in all_ids if x in self._topology_nodes)
            created_links = set()
            for adjacent_node_id in adjacent_node_ids:
                adjacent_node = self._topology_nodes[adjacent_node_id]
                adjacent_node.outgoing.discard(remove_node.id)
                adjacent_node.incoming.discard(remove_node.id)
                for other_adjacent_node_id in adjacent_node_ids:
                    if adjacent_node_id == other_adjacent_node_id:
                        continue
                    # Only link elements once in one direction
                    link_id = tuple(sorted([adjacent_node_id, other_adjacent_node_id]))
                    if link_id in created_links:
                        continue
                    self._topology_nodes[adjacent_node_id].outgoing.add(other_adjacent_node_id)
                    self._topology_nodes[other_adjacent_node_id].outgoing.add(adjacent_node_id)
                    created_links.add(link_id)
            self._topology_nodes.pop(remove_node.id)

        # Depending on the configuration, remove service nodes and link hosts directly
        for node_id, node in list(self._topology_nodes.items()):
            if node.type not in (
                NodeType.TOPOLOGY_SERVICE,
                NodeType.TOPOLOGY_UNKNOWN_SERVICE,
            ):
                continue

            visibility = general_service_visibility

            # A host may disable its services
            # Check if the host is also present in this data and use its visibility setting
            core_entity = self._network_data.core_entity_for_id(node_id)
            if core_entity is not None:
                host_id = self._network_data.hostname.get(core_entity[0])
                if host_id and (
                    custom_settings
                    := self._topology_configuration.frontend.custom_node_settings.get(host_id)
                ):
                    visibility = custom_settings.get("show_services", general_service_visibility)
            if visibility == "all":
                continue
            if visibility == "none" or self._node_extra_info.get(node_id, {}).get("state") == 0:
                remove_service(node)

    def _enrich_nodes_with_core_data(self) -> None:
        # Enrich with data from core and adjust node_type
        core_hostnames = set()
        core_services = set()
        for node_id, node in self._topology_nodes.items():
            node.type = NodeType.TOPOLOGY_UNKNOWN
            if core_entity := self._network_data.core_entity_for_id(node_id):
                if isinstance(core_entity, str):
                    core_hostnames.add(HostName(core_entity))
                else:
                    core_services.add((HostName(core_entity[0]), core_entity[1]))

        core_data_provider = _core_data_provider()
        core_data_provider.fetch_host_info(core_hostnames)
        core_data_provider.fetch_service_info(core_services)

        for node_id, node in self._topology_nodes.items():
            if core_entity := self._network_data.core_entity_for_id(node_id):
                extra_info: dict[str, Any] = {}
                if isinstance(core_entity, tuple):
                    extra_info.update({"hostname": core_entity[0], "service": core_entity[1]})
                    if service_info := core_data_provider.core_services.get(
                        (HostName(core_entity[0]), core_entity[1])
                    ):
                        node.type = NodeType.TOPOLOGY_SERVICE
                        extra_info.update(
                            {
                                "site": service_info.site,
                                "icon": (
                                    theme.detect_icon_path(service_info.icon_image, "icon_")
                                    if service_info.icon_image
                                    else None
                                ),
                                "state": service_info.state,
                            }
                        )
                    else:
                        node.type = NodeType.TOPOLOGY_UNKNOWN_SERVICE
                else:
                    extra_info.update({"hostname": core_entity})
                    if host_info := core_data_provider.core_hosts.get(core_entity):
                        node.type = NodeType.TOPOLOGY_HOST
                        extra_info.update(
                            {
                                "site": host_info.site,
                                "icon": (
                                    theme.detect_icon_path(host_info.icon_image, "icon_")
                                    if host_info.icon_image
                                    else None
                                ),
                                "state": host_info.state,
                                "has_been_checked": host_info.has_been_checked,
                                "num_services_warn": host_info.num_services_warn,
                                "num_services_crit": host_info.num_services_crit,
                            }
                        )
                    else:
                        node.type = NodeType.TOPOLOGY_UNKNOWN_HOST
                self._node_extra_info[node_id] = extra_info


def _resolve_circular_mesh_depths(
    explicit_start_nodes: list[TopologyNode], circular_nodes: TopologyNodes
) -> None:
    """Computes mesh_depth information for node meshes which have no actual start
    The computed root nodes have mesh_depth 1"""
    for node in explicit_start_nodes:
        node.mesh_depth = 1

    nodes_by_num_connections = []
    for node_id, node in circular_nodes.items():
        node.mesh_depth = 1
        total_connections = len(node.incoming.union(node.outgoing))
        nodes_by_num_connections.append((total_connections, node))
    nodes_by_num_connections.sort(key=lambda x: x[0], reverse=True)

    traversed_nodes = set()
    for start_node in explicit_start_nodes + list(x[1] for x in nodes_by_num_connections):
        mesh_depth = 1
        if start_node.id in traversed_nodes:
            continue
        traversed_nodes.add(start_node.id)
        next_node_ids = [start_node.id]
        # Note: Using a recursive approach will NOT work, because of circles in the mesh
        #       Grow from the start, then hop once in every direction with each cycle
        while next_node_ids:
            mesh_depth += 1
            upcoming_nodes = set()
            for node_id in next_node_ids:
                node = circular_nodes[node_id]
                for adjacent_id in node.incoming.union(node.outgoing):
                    if adjacent_id in traversed_nodes:
                        continue
                    traversed_nodes.add(node.id)
                    if adjacent_node := circular_nodes.get(adjacent_id):
                        adjacent_node.mesh_depth = mesh_depth
                        upcoming_nodes.add(adjacent_id)
            next_node_ids = sorted(upcoming_nodes)


class Topology:
    """Generates SerializedNodeConfig for frontend"""

    def __init__(
        self,
        topology_configuration: TopologyConfiguration,
        enforce_datasource: str | None = None,
    ) -> None:
        self._topology_configuration = topology_configuration
        self._root_hostnames_from_core = _get_hostnames_from_core(self._topology_configuration)
        self._growth_root_nodes = self._topology_configuration.frontend.growth_root_nodes_set.union(
            self._root_hostnames_from_core
        )
        self._compare_to_topology: Topology | None = None
        ds_config = self._topology_configuration.frontend.datasource_configuration
        used_datasource = enforce_datasource if enforce_datasource else ds_config.reference
        self._computed_layers = self._get_computed_layers(topology_data_dir / used_datasource)
        self._merged_results, self._node_specific_infos = self._combine_results(
            self._computed_layers,
            topology_configuration.frontend.overlays_config.computation_options.merge_nodes,
        )

    @property
    def growth_root_nodes(self) -> set[str]:
        return self._growth_root_nodes

    @property
    def computed_layers(self) -> dict[str, ABCTopologyNodeDataGenerator]:
        return self._computed_layers

    @property
    def merged_results(self) -> dict[str, TopologyNode]:
        return self._merged_results

    @property
    def node_specific_infos(self) -> dict[str, Any]:
        return self._node_specific_infos

    def _get_computed_layers(self, data_folder: Path) -> dict[str, ABCTopologyNodeDataGenerator]:
        computed_layers = {}
        active_layer_ids = [
            layer_id
            for layer_id, overlay_config in self._topology_configuration.frontend.overlays_config.overlays.items()
            if overlay_config.get("active")
        ]

        for layer_id in active_layer_ids:
            layer_class = topology_layer_registry.get(layer_id)
            layer = None
            if layer_class:
                layer = layer_class(
                    set(map(str, self._root_hostnames_from_core)),
                    self._topology_configuration,
                    data_folder,
                    add_data_root_node=len(active_layer_ids) > 1,
                )
            elif layer_id.startswith(_dynamic_network_data_id("")):
                # Create generic class instances for dynamic layers
                layer = GenericNetworkDataGenerator(
                    layer_id.removeprefix("network@"),
                    self._root_hostnames_from_core,
                    self._topology_configuration,
                    data_folder,
                    add_data_root_node=len(active_layer_ids) > 1,
                )
            if layer:
                computed_layers[layer_id] = layer
            else:
                logger.warning("Found no layer class for %s", layer_id)
        return computed_layers

    def _combine_results(
        self,
        computed_layers: dict[str, ABCTopologyNodeDataGenerator],
        merge_nodes: bool,
    ) -> tuple[TopologyNodes, dict[str, Any]]:
        node_specific_infos: dict[str, Any] = {}

        layer_results = {x: y.get_topology_result() for x, y in computed_layers.items()}

        def add_id_prefix(prefixed_node: TopologyNode, prefix: str = "") -> None:
            prefixed_node.id = f"{prefix}{prefixed_node.id}"
            prefixed_node.incoming = {f"{prefix}{x}" for x in prefixed_node.incoming}
            prefixed_node.outgoing = {f"{prefix}{x}" for x in prefixed_node.outgoing}

        common_nodes: dict[str, list[str]] = {}
        merged_results: dict[str, TopologyNode] = {}
        for idx, (layer_id, layer_result) in enumerate(layer_results.items()):
            for node_id, node in layer_result.items():
                common_nodes.setdefault(node_id, []).append(layer_id)

                # Fetch node specific info, before the node gets an optional renaming
                node_specific_info = computed_layers[layer_id].get_node_specific_info(node)
                if not merge_nodes and idx > 0:
                    # The nodes of each layer get a distinct id except the first layer
                    # Reason: This reduces flickering in the GUI frontend, because the node_id
                    # stays the same for some nodes, even if the mode is switched
                    add_id_prefix(node, f"{layer_id}_")
                if existing_node := merged_results.get(node.id):
                    node.outgoing.update(existing_node.outgoing)
                    node.incoming.update(existing_node.incoming)
                merged_results[node.id] = node
                node_specific_infos.setdefault(node.id, {}).update(node_specific_info)

        return merged_results, node_specific_infos


def compute_node_config(
    merged_results: TopologyNodes,
    node_specific_infos: dict[str, Any],
    topology_configuration: TopologyConfiguration,
    growth_root_nodes: set[str],
) -> tuple[HierarchyNode, set[str]]:
    topology_center = HierarchyNode(
        id=NodeType.TOPOLOGY_CENTER.value,
        name=NodeType.TOPOLOGY_CENTER.value,
        node_type=NodeType.TOPOLOGY_CENTER.value,
        children=[],
    )
    all_node_ids = set(merged_results.keys())

    # Compute node info
    all_frontend_nodes: dict[str, HierarchyNode] = {}
    for node_id, node in merged_results.items():
        all_frontend_nodes[node_id] = HierarchyNode(
            id=node.id,
            name=node.name,
            node_type=node.type.value,
            children=[],  # Will be filled later on
            growth_settings=_compute_growth_settings(
                node, all_node_ids, growth_root_nodes, topology_configuration.frontend
            ),
            type_specific=node_specific_infos.get(node_id, {}),
        )

    assigned_node_ids: set[str] = set()
    hosts_to_assign: dict[HostName, list[HierarchyNode]] = {}
    services_to_assign: dict[str, HierarchyNode] = {}
    for node_id, frontend_node in all_frontend_nodes.items():
        if core_entity := frontend_node.type_specific.get("core"):
            if "service" in core_entity:
                services_to_assign[node_id] = frontend_node
            else:
                hosts_to_assign.setdefault(HostName(core_entity["hostname"]), []).append(
                    frontend_node
                )

    computation_options = topology_configuration.frontend.overlays_config.computation_options
    if computation_options.hierarchy == "flat":
        _flatten_hierarchy(merged_results, hosts_to_assign, services_to_assign)
    if computation_options.enforce_hierarchy_update:
        match computation_options.hierarchy:
            case "flat":
                topology_configuration.layout = _get_default_layout("radial")
            case "full":
                topology_configuration.layout = _get_default_layout("hierarchy")
    computation_options.enforce_hierarchy_update = False

    _assign_services_to_hosts(
        merged_results, hosts_to_assign, services_to_assign, assigned_node_ids
    )

    nodes_by_depth: dict[int, TopologyNodes] = {}
    for node_id, node in merged_results.items():
        nodes_by_depth.setdefault(node.mesh_depth, {})[node_id] = node

    # logger.warning("NODES BY DEPTH")
    # for depth, values in sorted(list(nodes_by_depth.items())):
    #     logger.warning(f"Depth {depth}")
    #     logger.warning(pprint.pformat(values.keys()))

    _build_children_hierarchy(
        nodes_by_depth,
        all_frontend_nodes,
        assigned_node_ids,
        topology_configuration.filter.max_nodes,
    )

    topology_center.children = [all_frontend_nodes[x] for x, y in nodes_by_depth.get(0, {}).items()]
    for frontend_node in list(all_frontend_nodes.values()) + [topology_center]:
        frontend_node.children.sort(key=lambda x: _convert_to_sort_tuple(x.name))

    return topology_center, assigned_node_ids


def _flatten_hierarchy(
    merged_results: TopologyNodes,
    hosts_to_assign: dict[HostName, list[HierarchyNode]],
    services_to_assign: dict[str, HierarchyNode],
) -> None:
    # Goal: Step1: Move all non-root nodes to mesh_depth 0
    #       Step2: Services with a known hosts are set to mesh_depth 1
    for node in merged_results.values():
        node.mesh_depth = 0

    for service_id, service_node in sorted(services_to_assign.items()):
        hostname = service_node.type_specific["core"]["hostname"]
        possible_hosts = hosts_to_assign.get(hostname, [])
        if len(possible_hosts) == 1:
            merged_results[service_id].mesh_depth = 1


def _assign_services_to_hosts(
    merged_results: dict[str, TopologyNode],
    hosts_to_assign: dict[HostName, list[HierarchyNode]],
    services_to_assign: dict[str, HierarchyNode],
    assigned_node_ids: set[str],
) -> None:
    # Goal: Services are assigned to their host, if host has a lower depth
    for service_id, service_node in sorted(services_to_assign.items()):
        hostname = service_node.type_specific["core"]["hostname"]
        possible_hosts = hosts_to_assign.get(hostname, [])
        if not possible_hosts:
            continue
        first_host = possible_hosts[0]

        host_depth = merged_results[first_host.id].mesh_depth
        own_depth = merged_results[service_id].mesh_depth
        if own_depth > host_depth:
            first_host.children.append(service_node)
            assigned_node_ids.add(service_id)


def _build_children_hierarchy(
    nodes_by_depth: dict[int, TopologyNodes],
    all_frontend_nodes: dict[str, HierarchyNode],
    assigned_node_ids: set[str],
    max_nodes: int,
) -> None:
    if not nodes_by_depth:
        return

    sorted_nodes_by_depth = []
    for _depth, nodes in sorted(nodes_by_depth.items()):
        sorted_nodes_by_depth.extend(sorted(nodes.keys()))

    def get_node_with_lowest_depth(check_ids: set[str]) -> HierarchyNode:
        # There might be unknown nodes in the node_ids, but never all unknown
        lowest_index = 100000
        for check_id in check_ids:
            try:
                lowest_index = min(sorted_nodes_by_depth.index(check_id), lowest_index)
            except ValueError:
                continue
        return all_frontend_nodes[sorted_nodes_by_depth[lowest_index]]

    def assign_node(
        parent_node: HierarchyNode, child_node: HierarchyNode, processed_id: str
    ) -> None:
        parent_node.children.append(child_node)
        assigned_node_ids.add(processed_id)
        if len(assigned_node_ids) > max_nodes:
            raise MKGrowthExceeded()

    # Depth 0 nodes are always automatically assigned to the topology_central node
    assigned_node_ids.update(list(nodes_by_depth[0].keys()))
    try:
        for i in range(0, max(nodes_by_depth.keys()) + 1):
            # logger.warning(f"CHECKING LEVEL {i}")
            nodes_of_depth = nodes_by_depth[i]
            for node_id, node_result in sorted(list(nodes_of_depth.items())):
                all_other_ids = {
                    x
                    for x in node_result.incoming.union(node_result.outgoing)
                    if x in all_frontend_nodes
                }

                # logger.warning(f"checking node {node_id}   -> others {all_other_ids}")
                own_frontend_node = all_frontend_nodes[node_id]
                # Assign others to self
                for other_id in sorted(all_other_ids):
                    if other_id not in assigned_node_ids:
                        other_frontend_node = all_frontend_nodes[other_id]
                        # logger.warning(f" assign {other_id} to {node_id}")
                        assign_node(own_frontend_node, other_frontend_node, other_id)

                # Assign self to lower layers if not assigned, yet
                if node_id not in assigned_node_ids and i > 0:
                    other_lower_layer_node = get_node_with_lowest_depth(
                        node_result.incoming.union(node_result.outgoing)
                    )
                    # logger.warning(f" assign self {node_id} to {other_lower_layer_node.id}")
                    assign_node(other_lower_layer_node, own_frontend_node, node_id)
    except MKGrowthExceeded:
        pass


def _compute_growth_settings(
    node: TopologyNode,
    all_node_ids: set[str],
    growth_root_nodes: set[str],
    frontend: FrontendConfiguration,
) -> GrowthSettings:
    def growth_possible(check_node: TopologyNode) -> bool:
        border_hosts = check_node.incoming.union(check_node.outgoing)
        return len(border_hosts - all_node_ids) > 0

    return GrowthSettings(
        growth_root=node.id in frontend.growth_root_nodes,
        growth_continue=node.id in frontend.growth_continue_nodes,
        growth_forbidden=node.id in frontend.growth_forbidden_nodes,
        indicator_growth_possible=growth_possible(node),
        indicator_growth_root=node.id in growth_root_nodes,
    )


_type_to_base_type = {
    NodeType.TOPOLOGY_UNKNOWN_HOST: NodeType.TOPOLOGY_HOST,
    NodeType.TOPOLOGY_UNKNOWN_SERVICE: NodeType.TOPOLOGY_SERVICE,
    NodeType.TOPOLOGY_UNKNOWN: NodeType.TOPOLOGY_HOST,
}


def _link_type(node1: TopologyNode, node2: TopologyNode) -> str:
    node1_type = _type_to_base_type.get(node1.type, node1.type)
    node2_type = _type_to_base_type.get(node2.type, node2.type)
    if node1_type == node2_type:
        if node1_type == NodeType.TOPOLOGY_HOST:
            return TopologyLinkType.HOST2HOST.value
        if node1_type == NodeType.TOPOLOGY_SERVICE:
            return TopologyLinkType.SERVICE2SERVICE.value
    if (node1_type == NodeType.TOPOLOGY_SERVICE and node2_type == NodeType.TOPOLOGY_HOST) or (
        node1_type == NodeType.TOPOLOGY_HOST and node2_type == NodeType.TOPOLOGY_SERVICE
    ):
        return TopologyLinkType.HOST2SERVICE.value
    return TopologyLinkType.DEFAULT.value


def _get_link_config(
    start_node: TopologyNode,
    end_node: TopologyNode,
    computed_layers: dict[str, ABCTopologyNodeDataGenerator],
) -> dict[str, Any]:
    config = {"type": _link_type(start_node, end_node)}
    # Add/Merge link metadata from all involved layers
    for layer in computed_layers.values():
        if link_metadata := layer.link_metadata.get((start_node.id, end_node.id)):
            config.update(link_metadata)
    return config


def _compute_mesh_links(topology: Topology) -> list[TopologyLink]:
    merged_results: dict[str, TopologyNode] = topology.merged_results
    computed_layers: dict[str, ABCTopologyNodeDataGenerator] = topology.computed_layers
    mesh_links: dict[int, TopologyLink] = {}

    def add_mesh_link(link: TopologyLink) -> None:
        # Ensure that only one link is specified, but merged configurations of duplicate links
        if existing_link := mesh_links.get(hash(link)):
            existing_link.config.update(link.config)
        else:
            mesh_links[hash(link)] = link

    for node_id, node in list(merged_results.items()):
        for incoming_node_id in node.incoming:
            if incoming_node_id not in merged_results:
                continue
            new_link = TopologyLink(
                incoming_node_id,
                node_id,
            )
            new_link.config = _get_link_config(
                node, merged_results[incoming_node_id], computed_layers
            )
            add_mesh_link(new_link)
        for outgoing_node_id in node.outgoing:
            if outgoing_node_id not in merged_results:
                continue
            new_link = TopologyLink(
                node_id,
                outgoing_node_id,
            )
            new_link.config = _get_link_config(
                node, merged_results[outgoing_node_id], computed_layers
            )
            add_mesh_link(new_link)

    return list(mesh_links.values())


class TopologyLayerRegistry(cmk.ccc.plugin_registry.Registry[type[ABCTopologyNodeDataGenerator]]):
    def plugin_name(self, instance: type[ABCTopologyNodeDataGenerator]) -> str:
        return instance.ident


topology_layer_registry = TopologyLayerRegistry()


def _register_builtin_views() -> None:
    multisite_builtin_views.update(
        {
            "topology_filters": {
                "browser_reload": 30,
                "column_headers": "pergroup",
                "datasource": "hosts",
                "description": _l(
                    "Configures the number of available filters in the network topology view."
                ),
                "group_painters": [],
                "hidden": True,
                "hidebutton": True,
                "layout": "table",
                "mustsearch": False,
                "name": "topology_filters",
                "num_columns": 3,
                "owner": UserId.builtin(),
                "painters": [ColumnSpec(name="host_state")],
                "play_sounds": False,
                "public": True,
                "sorters": [],
                "title": _l("Topology filters"),
                "topic": "Topology",
                "user_sortable": True,
                "single_infos": [],
                "context": {
                    "topology_max_nodes": {},
                    "topology_mesh_depth": {},
                    "hoststate": {},
                    "hostalias": {},
                    "siteopt": {},
                    "hostregex": {},
                    "hostgroups": {},
                    "host_labels": {},
                    "opthost_contactgroup": {},
                    "host_tags": {},
                },
                "link_from": {},
                "icon": None,
                "add_context_to_title": True,
                "sort_index": 99,
                "is_show_more": False,
                "packaged": False,
                "main_menu_search_terms": [],
            },
            "topology_hover_host": {
                "browser_reload": 0,
                "column_headers": "pergroup",
                "datasource": "hosts",
                "description": _l("Host hover menu shown in topology visualization"),
                "hidden": True,
                "hidebutton": True,
                "group_painters": [],
                "icon": None,
                "layout": "dataset",
                "mobile": False,
                "mustsearch": False,
                "name": "topology_hover_host",
                "num_columns": 1,
                "owner": UserId.builtin(),
                "painters": [
                    ColumnSpec(
                        name="host",
                        parameters=PainterParameters(color_choices=[]),
                        link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
                    ),
                    ColumnSpec(name="host_state"),
                    ColumnSpec(name="host_plugin_output"),
                    ColumnSpec(name="host_parents"),
                    ColumnSpec(name="host_childs"),
                ],
                "play_sounds": False,
                "public": True,
                "single_infos": ["host"],
                "sorters": [],
                "title": _l("Toplogy host details"),
                "user_sortable": True,
                "context": {},
                "link_from": {},
                "topic": "",
                "add_context_to_title": True,
                "sort_index": 99,
                "is_show_more": False,
                "packaged": False,
                "main_menu_search_terms": [],
            },
            "topology_hover_service": {
                "add_context_to_title": True,
                "browser_reload": 30,
                "column_headers": "pergroup",
                "context": {},
                "datasource": "services",
                "description": "Information shown when hovering over a topology service noden",
                "force_checkboxes": False,
                "group_painters": [],
                "hidden": True,
                "hidebutton": False,
                "icon": None,
                "owner": UserId.builtin(),
                "is_show_more": False,
                "layout": "dataset",
                "link_from": {},
                "mobile": False,
                "mustsearch": False,
                "name": "topology_hover_service",
                "num_columns": 1,
                "packaged": False,
                "painters": [
                    ColumnSpec(name="service_state"),
                    ColumnSpec(
                        name="service_description",
                        link_spec=VisualLinkSpec(type_name="views", name="service"),
                    ),
                    ColumnSpec(name="service_icons"),
                    ColumnSpec(name="svc_plugin_output"),
                    ColumnSpec(name="svc_state_age"),
                    ColumnSpec(name="svc_check_age"),
                    ColumnSpec(name="perfometer"),
                    ColumnSpec(name="network_info"),
                ],
                "play_sounds": False,
                "public": True,
                "single_infos": ["service", "host"],
                "sort_index": 99,
                "sorters": [],
                "title": "Service",
                "topic": "other",
                "user_sortable": True,
                "main_menu_search_terms": [],
            },
        }
    )


def cleanup_topology_layouts(config: Config) -> None:
    """Topology layouts are currently restricted to a maximum number of 10000"""
    topology_configs_dir.mkdir(parents=True, exist_ok=True)

    # Do simply maximum size check
    maximum_files = 10000
    num_files = len(os.listdir(topology_configs_dir))
    if num_files < maximum_files:
        return

    with locked(topology_settings_lookup):
        topology_settings: dict[str, str] = store.try_load_file_from_pickle_cache(
            topology_settings_lookup,
            default={},
            temp_dir=cmk.utils.paths.tmp_dir,
            root_dir=cmk.utils.paths.omd_root,
        )
        reverse_lookup: dict[str, str] = {y: x for x, y in topology_settings.items()}
        paths = sorted(
            os.listdir(topology_configs_dir),
            key=lambda x: os.path.getmtime(os.path.join(topology_configs_dir, x)),
            reverse=True,
        )

        # Remove keys with non-existent files
        for unknown_file in set(reverse_lookup.keys()) - set(paths):
            topology_settings.pop(reverse_lookup[unknown_file], None)

        # Remove files exceeding limit
        for file_to_remove in paths[maximum_files:]:
            path_to_remove = topology_configs_dir / file_to_remove
            path_to_remove.unlink(missing_ok=True)
            topology_settings.pop(reverse_lookup.get(file_to_remove, ""), None)

        store.save_object_to_file(topology_settings_lookup, topology_settings)


def _create_filter_configuration_from_hash(
    hash_value: str,
) -> TopologyFilterConfiguration | None:
    # Try to create filter- and frontend configuration from this hash
    # This is quite ugly and will vanish once we have a better mechanism to save layouts
    all_query_ids_by_hash = {y: x for x, y in _all_settings().items()}
    query_spec = all_query_ids_by_hash.get(hash_value)
    if query_spec is None:
        return None

    _topology_type, max_nodes, mesh_depth, auto_nodes, query_string = query_spec
    return TopologyFilterConfiguration(
        mesh_depth=int(mesh_depth),
        max_nodes=int(max_nodes),
        growth_auto_max_nodes=int(auto_nodes),
        query=str(query_string),
    )


def get_topology_configuration(
    topology_type: str, default_overlays: OverlaysConfig
) -> TopologyConfiguration:
    # Get parameters from request
    topology_filters = _get_topology_settings_from_filters()
    mesh_depth = int(topology_filters["topology_mesh_depth"])
    max_nodes = int(topology_filters["topology_max_nodes"])
    filter_configuration = TopologyFilterConfiguration(
        mesh_depth=mesh_depth, max_nodes=max_nodes, query=_get_query_string()
    )
    # Check if the request includes a frontend_configuration -> AJAX request
    frontend_configuration = _get_frontend_configuration_from_request()
    if frontend_configuration:
        layout = Layout(**json.loads(request.get_str_input_mandatory("layout")))
        return TopologyConfiguration(
            type=topology_type,
            frontend=frontend_configuration,
            filter=filter_configuration,
            layout=layout,
        )

    # Check if there is a saved topology for this filter
    query_identifier = TopologyQueryIdentifier(topology_type, filter_configuration)
    serialized_settings = _get_topology_config_for_query(query_identifier)
    if serialized_settings:
        topology_configuration = TopologyConfiguration.parse(serialized_settings, query_identifier)
        # Since we do not save the available_overlays in the settings we have to add them
        topology_configuration.frontend.overlays_config.available_layers = (
            default_overlays.available_layers
        )
        return topology_configuration

    # Fallback, new page, no saved settings
    frontend_configuration = FrontendConfiguration()
    frontend_configuration.overlays_config = default_overlays

    return TopologyConfiguration(
        type=topology_type,
        frontend=frontend_configuration,
        filter=filter_configuration,
        layout=_get_default_layout(),
    )


def _get_default_layout(style: Literal["hierarchy", "radial"] = "hierarchy") -> Layout:
    default_layout = Layout()
    match style:
        case "hierarchy":
            default_layout.style_configs = [
                {
                    "type": "hierarchy",
                    "options": {
                        "box_leaf_nodes": False,
                        "layer_height": 180,
                        "node_size": 15,
                        "rotation": 0,
                    },
                    "position": {
                        "x": 3,
                        "y": 50,
                    },
                    "matcher": {"id": {"value": NodeType.TOPOLOGY_CENTER.value}},
                }
            ]
            default_layout.line_config = {"style": "straight"}
        case "radial":
            default_layout.style_configs = [
                {
                    "type": "radial",
                    "options": {
                        "radius": 120,
                        "degree": 360,
                        "rotation": 0,
                    },
                    "position": {
                        "x": 50,
                        "y": 50,
                    },
                    "matcher": {"id": {"value": NodeType.TOPOLOGY_CENTER.value}},
                }
            ]
            default_layout.line_config = {"style": "round"}
    return default_layout


def _get_topology_settings_from_filters() -> dict[str, str]:
    topology_values: dict[str, str] = {}
    for filter_class in (FilterTopologyMaxNodes, FilterTopologyMeshDepth):
        filter_instance = filter_class()
        value = filter_instance.value()
        if not value[filter_instance.ident].isdigit():
            value = {filter_instance.ident: filter_instance.range_config.default}
        topology_values.update(value)
    return topology_values


def _get_query_string() -> str:
    # Determine hosts from filters
    filter_headers = "".join(get_livestatus_filter_headers(*get_topology_context_and_filters()))
    query = "GET hosts\nColumns: name"
    if filter_headers:
        query += "\n%s" % filter_headers
    return query


def _layout_path(topology_hash: str) -> Path:
    return topology_configs_dir / topology_hash


def _get_topology_config_for_hash(topology_hash: str) -> dict[str, Any]:
    topology_file = _layout_path(topology_hash)
    if not topology_file.exists():
        return {}

    topology_file.touch()  # Used for last usage statistics
    try:
        return json.loads(store.load_text_from_file(topology_file))
    except json.JSONDecodeError:
        return {}


def _get_topology_config_for_query(
    query_identifier: TopologyQueryIdentifier,
) -> dict[str, Any]:
    if not topology_settings_lookup.exists():
        return {}

    found_topology_hash = _all_settings().get(query_identifier.identifier)
    if found_topology_hash is None:
        return {}

    return _get_topology_config_for_hash(found_topology_hash)


def _all_settings() -> dict[tuple[str, ...], str]:
    return store.try_load_file_from_pickle_cache(
        topology_settings_lookup,
        default={},
        temp_dir=cmk.utils.paths.tmp_dir,
        root_dir=cmk.utils.paths.omd_root,
    )


def _get_frontend_configuration_from_request() -> None | FrontendConfiguration:
    if frontend_config := request.get_str_input("topology_frontend_configuration"):
        return FrontendConfiguration.parse(json.loads(frontend_config))
    return None


def _dynamic_network_data_id(layer_id: str) -> str:
    return f"network@{layer_id}"


def _get_dynamic_layer_ids(
    topology_configuration: TopologyConfiguration | None = None,
) -> list[str]:
    check_folders = set(
        str(path) for path in Path(topology_data_dir).glob("*") if Path(path).is_dir()
    )
    if topology_configuration:
        check_folders.add(topology_configuration.frontend.datasource_configuration.reference)
        check_folders.add(topology_configuration.frontend.datasource_configuration.compare_to)
    dynamic_layer_ids = set()
    for folder in check_folders:
        for filename in glob.glob("data_*.json", root_dir=topology_data_dir / folder):
            dynamic_layer_ids.add(
                _dynamic_network_data_id(filename.removeprefix("data_").removesuffix(".json"))
            )
    return list(dynamic_layer_ids)


def _get_hostnames_from_core(
    topology_configuration: TopologyConfiguration,
) -> set[HostName]:
    site_id = (
        SiteId(request.get_str_input_mandatory("site")) if request.get_str_input("site") else None
    )
    with sites.only_sites(site_id), sites.set_limit(topology_configuration.filter.max_nodes):
        return {x[0] for x in sites.live().query(topology_configuration.filter.query)}


def _compute_topology_response(
    topology_configuration: TopologyConfiguration,
) -> dict[str, Any]:
    # logger.warning(f"Initial topology {pprint.pformat(topology_configuration.frontend)}")
    ds_config = topology_configuration.frontend.datasource_configuration
    reference = Topology(topology_configuration, ds_config.reference)

    link_config_comparison: dict[TopologyLink, dict[str, Any]] = {}
    if ds_config.reference != ds_config.compare_to:
        compare_to = Topology(topology_configuration, ds_config.compare_to)
        # Compute link_config, will be used later on
        ref_mesh_links = _compute_mesh_links(reference)
        compare_mesh_links = _compute_mesh_links(compare_to)
        link_config_comparison = _compute_link_config_for_comparison(
            ref_mesh_links, compare_mesh_links
        )
        _integrate_node_changes_in_reference(reference, compare_to)
    else:
        # Always reset classes used in frontend
        for node in reference.node_specific_infos.values():
            node["topology_classes"] = [
                ["only_in_ref", False],
                ["missing_in_ref", False],
            ]

    result = _compute_topology_result(
        topology_configuration,
        reference,
        link_config_comparison,
    )

    # import pprint
    # logger.warning(f"Result {pprint.pformat(result)}")
    return asdict(result)


def _compute_link_config_for_comparison(
    reference_mesh_links: list[TopologyLink],
    compare_to_mesh_links: list[TopologyLink],
) -> dict[TopologyLink, dict[str, Any]]:
    ref_by_id = {x: "" for x in reference_mesh_links}
    compare_to_by_id = {x: "" for x in compare_to_mesh_links}

    extra_in_ref = set(ref_by_id) - set(compare_to_by_id)
    extra_in_com = set(compare_to_by_id) - set(ref_by_id)
    link_config = {}
    for link in extra_in_ref:
        link_config[link] = {"topology_classes": [["only_in_ref", True], ["missing_in_ref", False]]}
    for link in extra_in_com:
        link_config[link] = {"topology_classes": [["only_in_ref", False], ["missing_in_ref", True]]}

    return link_config


def _compute_topology_result(
    topology_configuration: TopologyConfiguration,
    topology: Topology,
    link_config_comparison: dict[TopologyLink, dict[str, Any]],
) -> TopologyResponse:
    active_layers: dict[str, ABCTopologyNodeDataGenerator] = topology.computed_layers
    merged_results: TopologyNodes = topology.merged_results
    node_specific_infos: dict[str, Any] = topology.node_specific_infos
    growth_root_nodes: set[str] = topology.growth_root_nodes

    headline = _("Topology for ") + ", ".join(layer.name() for layer in active_layers.values())

    if len(merged_results) > topology_configuration.filter.max_nodes:
        headline += _(" (data incomplete, maximum number of nodes reached)")

    topology_center, assigned_node_ids = compute_node_config(
        merged_results,
        node_specific_infos,
        topology_configuration,
        growth_root_nodes,
    )

    # Reduce mesh links without references
    mesh_links = _compute_mesh_links(topology)

    def mesh_link_visible(link: TopologyLink) -> bool:
        return link.source in assigned_node_ids and link.target in assigned_node_ids

    shown_mesh_links = list(filter(mesh_link_visible, mesh_links))
    for link in shown_mesh_links:
        if config := link_config_comparison.get(link):
            comparison_config = config
        else:
            comparison_config = {
                "topology_classes": [["only_in_ref", False], ["missing_in_ref", False]]
            }
        link.config.update(comparison_config)

    frontend_config = NodeConfig(topology_center, shown_mesh_links)

    return TopologyResponse(
        frontend_config,
        topology_configuration.frontend,
        topology_configuration.layout,
        headline,
        [],
        query_hash=request.get_str_input("query_hash"),
    )


def _integrate_node_changes_in_reference(
    reference: Topology,
    compare_to: Topology,
) -> None:
    ref_merged_results = reference.merged_results
    ref_node_specific_infos = reference.node_specific_infos

    compare_merged_results = compare_to.merged_results
    compare_node_specific_infos = compare_to.node_specific_infos

    # integrate changes into reference and highlight differences
    extra_in_ref = set(ref_merged_results) - set(compare_merged_results)
    extra_in_com = set(compare_merged_results) - set(ref_merged_results)
    for node_id, node in ref_node_specific_infos.items():
        node["topology_classes"] = [["only_in_ref", False], ["missing_in_ref", False]]
    for node_id in extra_in_com:
        new_node = compare_merged_results[node_id]
        ref_node_specific_infos[node_id] = compare_node_specific_infos.get(node_id, {})
        ref_node_specific_infos[node_id]["topology_classes"] = [
            ["missing_in_ref", True],
            ["only_in_ref", False],
        ]
        ref_merged_results[node_id] = new_node
    for node_id in extra_in_ref:
        ref_node_specific_infos.setdefault(node_id, {})["topology_classes"] = [
            ["missing_in_ref", False],
            ["only_in_ref", True],
        ]


def _convert_to_sort_tuple(name: str) -> tuple:
    def try_int(value: str) -> str | int:
        try:
            return int(value)
        except ValueError:
            return value

    return tuple(map(try_int, re.split(r"(\d+)", name)))
