#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
import time
from typing import Any

from cmk.ccc.user import UserId

from cmk.gui import bi as bi
from cmk.gui.bi import bi_config_aggregation_function_registry
from cmk.gui.breadcrumb import make_simple_page_breadcrumb
from cmk.gui.config import Config
from cmk.gui.htmllib.header import make_header
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.main_menu import main_menu_registry
from cmk.gui.nodevis.filters import FilterTopologyMaxNodes, FilterTopologyMeshDepth
from cmk.gui.nodevis.utils import BILayoutManagement, get_toggle_layout_designer_page_menu_entry
from cmk.gui.page_menu import make_display_options_dropdown, PageMenu, PageMenuTopic
from cmk.gui.pages import AjaxPage, PageEndpoint, PageRegistry, PageResult
from cmk.gui.theme.current_theme import theme
from cmk.gui.type_defs import ColumnSpec, PainterParameters, VisualLinkSpec
from cmk.gui.utils.csrf_token import check_csrf_token
from cmk.gui.views.icon import IconRegistry
from cmk.gui.views.store import multisite_builtin_views
from cmk.gui.visuals.filter import FilterRegistry

from cmk.bi.aggregation_functions import BIAggregationFunctionSchema
from cmk.bi.computer import BIAggregationFilter
from cmk.bi.lib import NodeResultBundle
from cmk.bi.trees import BICompiledLeaf, BICompiledRule


def register(
    page_registry: PageRegistry,
    filter_registry: FilterRegistry,
    _icon_and_action_registry: IconRegistry,
) -> None:
    page_registry.register(PageEndpoint("ajax_fetch_aggregation_data", AjaxFetchAggregationData))
    page_registry.register(
        PageEndpoint("ajax_save_bi_aggregation_layout", AjaxSaveBIAggregationLayout)
    )
    page_registry.register(
        PageEndpoint("ajax_delete_bi_aggregation_layout", AjaxDeleteBIAggregationLayout)
    )
    page_registry.register(
        PageEndpoint("ajax_load_bi_aggregation_layout", AjaxLoadBIAggregationLayout)
    )
    page_registry.register(PageEndpoint("bi_map", _bi_map))
    filter_registry.register(FilterTopologyMeshDepth())
    filter_registry.register(FilterTopologyMaxNodes())
    _register_builtin_views()


class AjaxFetchAggregationData(AjaxPage):
    def page(self, config: Config) -> PageResult:
        aggregations_var = request.get_str_input_mandatory("aggregations", "[]")
        filter_names = json.loads(aggregations_var)

        bi_aggregation_filter = BIAggregationFilter([], [], [], filter_names, [], [])
        results = bi.BIManager().computer.compute_result_for_filter(bi_aggregation_filter)

        aggregation_info: dict[str, Any] = {"aggregation": {}}

        aggregation_layouts = BILayoutManagement.get_all_bi_aggregation_layouts()

        # Currently only one aggregation can be shown at a time
        for bi_compiled_aggregation, node_result_bundles in results:
            for node_result_bundle in node_result_bundles:
                branch = node_result_bundle.instance
                aggr_name = branch.properties.title
                visual_mapper = NodeVisualizationBIDataMapper(
                    is_single_host_aggregation=len(branch.get_required_hosts()) == 1
                )
                hierarchy = visual_mapper.consume(node_result_bundle, 1, {})

                data: dict[str, Any] = {}
                data["type"] = "bi"
                data["hierarchy"] = hierarchy
                # data["groups"] = bi_compiled_aggregation.groups.names
                data["data_timestamp"] = int(time.time())

                aggr_settings = bi_compiled_aggregation.aggregation_visualization
                layout: dict[str, Any] = {}
                if aggr_name in aggregation_layouts:
                    layout = aggregation_layouts[aggr_name]
                    layout["ignore_rule_styles"] = True
                    layout["origin_type"] = "explicit"
                    layout["origin_info"] = _("Explicit set")
                    layout["explicit_id"] = aggr_name
                else:
                    layout.update(self._get_template_based_layout_settings(aggr_settings, config))
                layout.setdefault("force_config", {})

                if "ignore_rule_styles" not in layout:
                    layout["ignore_rule_styles"] = aggr_settings.get("ignore_rule_styles", False)
                if "line_config" not in layout:
                    layout["line_config"] = self._get_line_style_config(aggr_settings, config)

                aggregation_info["node_config"] = data
                aggregation_info["layout"] = layout

        return aggregation_info

    def _get_line_style_config(
        self, aggr_settings: dict[str, Any], config: Config
    ) -> dict[str, Any]:
        line_style = aggr_settings.get("line_style", config.default_bi_layout["line_style"])
        if line_style == "default":
            line_style = config.default_bi_layout["line_style"]
        return {"style": line_style}

    def _get_template_based_layout_settings(
        self, aggr_settings: dict[str, Any], config: Config
    ) -> dict[str, Any]:
        template_layout_id = aggr_settings.get("layout_id", "builtin_default")

        layout_settings: dict[str, Any] = {}
        if template_layout_id.startswith("builtin_"):
            # FIXME: this mapping is currently copied from the bi configuration valuespec
            #        BI refactoring required...
            builtin_mapping = {
                "builtin_default": _("global"),
                "builtin_force": _("force"),
                "builtin_radial": _("radial"),
                "builtin_hierarchy": _("hierarchy"),
            }
            layout_settings["origin_type"] = "default_template"
            layout_settings["origin_info"] = _("Default %s template") % builtin_mapping.get(
                template_layout_id, _("Unknown")
            )

            if template_layout_id == "builtin_default":
                template_layout_id = config.default_bi_layout["node_style"]
            layout_settings["default_id"] = template_layout_id[8:]
        else:
            # Any Unknown/Removed layout id gets the default template
            layout_settings["origin_type"] = "default_template"
            layout_settings["origin_info"] = _("Fallback template (%s): Unknown ID %s") % (
                config.default_bi_layout["node_style"][8:].title(),
                template_layout_id,
            )
            layout_settings["default_id"] = config.default_bi_layout["node_style"][8:]

        return layout_settings


class NodeVisualizationBIDataMapper:
    def __init__(self, is_single_host_aggregation=False):
        super().__init__()
        self._is_single_host_aggregation = is_single_host_aggregation
        self._siblings: dict[str, int] = {}

    def consume(
        self,
        node_result_bundle: NodeResultBundle,
        depth: int,
        parent_node: dict[str, Any],
    ) -> dict[str, Any]:
        instance = node_result_bundle.instance
        if isinstance(instance, BICompiledRule):
            node_data = self._get_node_data_for_rule(instance)
        else:
            node_data = self._get_node_data_for_leaf(instance)

        actual_result = node_result_bundle.actual_result
        if isinstance(instance, BICompiledRule) and instance.properties.icon:
            node_data["icon"] = theme.detect_icon_path(instance.properties.icon, prefix="icon_")

        node_id, aggr_path, aggr_name = self._compute_node_indices(node_data, parent_node)
        node_data["id"] = node_id
        node_data["aggr_path_id"] = aggr_path
        node_data["aggr_path_name"] = aggr_name
        node_data.setdefault("type_specific", {}).setdefault("core", {})
        node_data["type_specific"]["core"].update(
            {
                "state": actual_result.state,
                "in_downtime": actual_result.in_downtime,
                "acknowledged": actual_result.acknowledged,
            }
        )

        node_data["children"] = []
        for nested_bundle in node_result_bundle.nested_results:
            node_data["children"].append(self.consume(nested_bundle, depth + 1, node_data))
        return node_data

    def _compute_node_indices(
        self, node_data: dict[str, Any], parent_node: dict[str, Any]
    ) -> tuple[str, list[tuple[str, int]], list[tuple[str, int]]]:
        """Computes three unique identifiers for each node
        - one for the node itself
        - one for the aggregation path name (based on computed names)
        - one for the aggregation path id (based on aggr/rule ids)
        """
        aggr_path_id: list = []
        aggr_path_name: list = []

        if parent_node:
            p_aggr_path_id = parent_node.get("aggr_path_id")
            if isinstance(p_aggr_path_id, list):
                aggr_path_id.extend(p_aggr_path_id)
            p_aggr_path_name = parent_node.get("aggr_path_name")
            if isinstance(p_aggr_path_name, list):
                aggr_path_name.extend(p_aggr_path_name)

        parent_id = parent_node.get("id", "")
        if rule_id := node_data.get("rule_id"):
            rule_name = node_data["name"]
            rule_name_idx = self._get_sibling_index("rule_name", parent_id + rule_name)
            own_id = f"#{rule_name}#{rule_name_idx}"
            aggr_path_id.append(
                [
                    rule_id["rule"],
                    self._get_sibling_index("rule_id", parent_id + rule_id["rule"]),
                ]
            )
            aggr_path_name.append([rule_name, rule_name_idx])
        else:
            core_info = node_data["type_specific"]["core"]
            hostname = core_info["hostname"]
            if service := core_info.get("service"):
                own_id = f"{service}({self._get_sibling_index('service', parent_id + service)})"
            else:
                own_id = f"{hostname}({self._get_sibling_index('hostname', parent_id + hostname)})"
        node_id = parent_id + own_id

        return node_id, aggr_path_id, aggr_path_name

    def _get_sibling_index(self, domain: str, value: str) -> int:
        key = f"{domain}_{value}"
        self._siblings.setdefault(key, 0)
        self._siblings[key] += 1
        return self._siblings[key]

    def _get_node_data_for_rule(self, bi_compiled_rule: BICompiledRule) -> dict[str, Any]:
        node_data: dict[str, Any] = {
            "node_type": "bi_aggregator",
            "name": bi_compiled_rule.properties.title,
        }

        aggregation_function = bi_compiled_rule.aggregation_function
        function_data = BIAggregationFunctionSchema().dump(aggregation_function)
        aggr_func_gui = bi_config_aggregation_function_registry[aggregation_function.kind()]

        node_data["rule_id"] = {
            "pack": bi_compiled_rule.pack_id,
            "rule": bi_compiled_rule.id,
            "aggregation_function_description": str(aggr_func_gui(function_data)),
        }
        node_data["rule_layout_style"] = bi_compiled_rule.node_visualization
        return node_data

    def _get_node_data_for_leaf(self, bi_compiled_leaf: BICompiledLeaf) -> dict[str, Any]:
        node_data: dict[str, Any] = {
            "node_type": "bi_leaf",
            "type_specific": {"core": {"hostname": bi_compiled_leaf.host_name}},
        }
        if not bi_compiled_leaf.service_description:
            node_data["name"] = bi_compiled_leaf.host_name
        else:
            node_data["type_specific"]["core"]["service"] = bi_compiled_leaf.service_description
            if self._is_single_host_aggregation:
                node_data["name"] = bi_compiled_leaf.service_description
            else:
                node_data["name"] = " ".join(
                    [bi_compiled_leaf.host_name, bi_compiled_leaf.service_description]
                )
        return node_data


class AjaxSaveBIAggregationLayout(AjaxPage):
    def page(self, config: Config) -> PageResult:
        check_csrf_token()
        layout_var = request.get_str_input_mandatory("layout", "{}")
        layout_config = json.loads(layout_var)
        config.bi_layouts["aggregations"].update(layout_config)
        BILayoutManagement.save_layouts()
        return {}


class AjaxDeleteBIAggregationLayout(AjaxPage):
    def page(self, config: Config) -> PageResult:
        check_csrf_token()
        for_aggregation = request.var("aggregation_name")
        config.bi_layouts["aggregations"].pop(for_aggregation)
        BILayoutManagement.save_layouts()
        return {}


class AjaxLoadBIAggregationLayout(AjaxPage):
    def page(self, config: Config) -> PageResult:
        aggregation_name = request.var("aggregation_name")
        return BILayoutManagement.load_bi_aggregation_layout(aggregation_name)


def _bi_map(config: Config) -> None:
    aggr_name = request.var("aggr_name")
    layout_id = request.var("layout_id")
    title = _("BI visualization")
    breadcrumb = make_simple_page_breadcrumb(main_menu_registry.menu_monitoring(), title)
    page_menu = PageMenu(breadcrumb=breadcrumb)
    display_dropdown = page_menu.get_dropdown_by_name("display", make_display_options_dropdown())
    display_dropdown.topics.insert(
        0,
        PageMenuTopic(
            title=_("Configuration"),
            entries=[get_toggle_layout_designer_page_menu_entry()],
        ),
    )
    make_header(html, title, breadcrumb, page_menu)

    div_id = "node_visualization"
    html.div("", id=div_id)
    html.javascript("node_instance = new cmk.nodevis.BIVisualization(%s);" % json.dumps(div_id))

    html.javascript(
        f"node_instance.show_aggregations({json.dumps([aggr_name])}, {json.dumps(layout_id)})"
    )


def _register_builtin_views():
    multisite_builtin_views.update(
        {
            "bi_map_hover_host": {
                "browser_reload": 0,
                "column_headers": "pergroup",
                "datasource": "hosts",
                "description": _l("Host hover menu shown in BI visualization"),
                "hidden": True,
                "hidebutton": True,
                "group_painters": [],
                "icon": None,
                "layout": "dataset",
                "mobile": False,
                "mustsearch": False,
                "name": "bi_map_hover_host",
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
                ],
                "play_sounds": False,
                "public": True,
                "single_infos": ["host"],
                "sorters": [],
                "title": _l("BI host details"),
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
            "bi_map_hover_service": {
                "browser_reload": 0,
                "column_headers": "pergroup",
                "datasource": "services",
                "description": _l("Service hover menu shown in BI visualization"),
                "hidden": True,
                "hidebutton": True,
                "group_painters": [],
                "icon": None,
                "layout": "dataset",
                "mobile": False,
                "mustsearch": False,
                "name": "bi_map_hover_service",
                "num_columns": 1,
                "painters": [
                    ColumnSpec(
                        name="host",
                        parameters=PainterParameters(color_choices=[]),
                        link_spec=VisualLinkSpec(type_name="views", name="hoststatus"),
                    ),
                    ColumnSpec(
                        name="service_description",
                        link_spec=VisualLinkSpec(type_name="views", name="service"),
                    ),
                    ColumnSpec(name="service_state"),
                    ColumnSpec(name="host_check_age"),
                    ColumnSpec(name="svc_acknowledged"),
                    ColumnSpec(name="svc_in_downtime"),
                ],
                "play_sounds": False,
                "public": True,
                "single_infos": ["service", "host"],
                "sorters": [],
                "title": _l("BI service details"),
                "owner": UserId.builtin(),
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
        }
    )
