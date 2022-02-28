#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type, Union

from livestatus import LivestatusOutputFormat, LivestatusResponse, OnlySites, SiteId

from cmk.utils.bi.bi_compiler import BICompiler
from cmk.utils.bi.bi_computer import BIAggregationFilter, BIComputer
from cmk.utils.bi.bi_data_fetcher import BIStatusFetcher
from cmk.utils.bi.bi_lib import BIStates, NodeResultBundle, SitesCallback
from cmk.utils.bi.bi_packs import BIAggregationPacks
from cmk.utils.bi.bi_trees import BICompiledRule
from cmk.utils.type_defs import HostName, ServiceName

import cmk.gui.i18n
import cmk.gui.pages
import cmk.gui.utils
import cmk.gui.utils.escaping as escaping
import cmk.gui.view_utils
import cmk.gui.watolib as watolib
from cmk.gui import sites
from cmk.gui.exceptions import MKConfigError
from cmk.gui.globals import config, html, output_funnel, request, theme, user
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    permission_registry,
    permission_section_registry,
    PermissionSection,
)
from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.type_defs import ColumnName, VisualContext
from cmk.gui.utils.urls import makeuri_contextless, urlencode_vars
from cmk.gui.valuespec import DropdownChoiceEntries


@permission_section_registry.register
class PermissionSectionBI(PermissionSection):
    @property
    def name(self):
        return "bi"

    @property
    def title(self):
        return _("BI - Checkmk Business Intelligence")


permission_registry.register(
    Permission(
        section=PermissionSectionBI,
        name="see_all",
        title=_l("See all hosts and services"),
        description=_l(
            "With this permission set, the BI aggregation rules are applied to all "
            "hosts and services - not only those the user is a contact for. If you "
            "remove this permissions then the user will see incomplete aggregation "
            "trees with status based only on those items."
        ),
        defaults=["admin", "guest"],
    )
)


def is_part_of_aggregation(host, service):
    if BIAggregationPacks.get_num_enabled_aggregations() == 0:
        return False
    return get_cached_bi_compiler().is_part_of_aggregation(host, service)


def get_aggregation_group_trees():
    # Here we have to deal with weird legacy
    # aggregation group definitions:
    # - "GROUP"
    # - ["GROUP_1", "GROUP2", ..]

    return get_cached_bi_packs().get_aggregation_group_trees()


def aggregation_group_choices() -> DropdownChoiceEntries:
    """Returns a sorted list of aggregation group names"""
    return get_cached_bi_packs().get_aggregation_group_choices()


def api_get_aggregation_state(
    filter_names: Optional[List[str]] = None, filter_groups: Optional[List[str]] = None
):
    bi_manager = BIManager()
    bi_aggregation_filter = BIAggregationFilter(
        [],
        [],
        [],
        filter_names or [],
        filter_groups or [],
        [],
    )

    def collect_infos(node_result_bundle: NodeResultBundle, is_single_host_aggregation: bool):
        actual_result = node_result_bundle.actual_result

        own_infos = {}
        if actual_result.custom_infos:
            own_infos["custom"] = actual_result.custom_infos

        if actual_result.state not in [BIStates.OK, BIStates.PENDING]:
            node_instance = node_result_bundle.instance
            line_tokens = []
            if isinstance(node_instance, BICompiledRule):
                line_tokens.append(node_instance.properties.title)
            else:
                node_info = []
                if not is_single_host_aggregation:
                    node_info.append(node_instance.host_name)
                if node_instance.service_description:
                    node_info.append(node_instance.service_description)
                if node_info:
                    line_tokens.append("/".join(node_info))
            if actual_result.output:
                line_tokens.append(actual_result.output)
            own_infos["error"] = {"state": actual_result.state, "output": ", ".join(line_tokens)}

        nested_infos = [
            x
            for y in node_result_bundle.nested_results
            for x in [collect_infos(y, is_single_host_aggregation)]
            if x is not None
        ]

        if own_infos or nested_infos:
            return [own_infos, nested_infos]
        return None

    aggregations = {}
    results = bi_manager.computer.compute_result_for_filter(bi_aggregation_filter)
    for _compiled_aggregation, node_result_bundles in results:
        for node_result_bundle in node_result_bundles:
            aggr_title = node_result_bundle.instance.properties.title
            required_hosts = [x[1] for x in node_result_bundle.instance.get_required_hosts()]
            is_single_host_aggregation = len(required_hosts) == 1
            aggregations[aggr_title] = {
                "state": node_result_bundle.actual_result.state,
                "hosts": required_hosts,
                "acknowledged": node_result_bundle.actual_result.acknowledged,
                "in_downtime": node_result_bundle.actual_result.downtime_state != 0,
                "in_service_period": node_result_bundle.actual_result.in_service_period,
                "infos": collect_infos(node_result_bundle, is_single_host_aggregation),
            }

    have_sites = {x[0] for x in bi_manager.status_fetcher.states}
    missing_aggregations = []
    required_sites = set()
    required_aggregations = bi_manager.computer.get_required_aggregations(bi_aggregation_filter)
    for _bi_aggregation, branches in required_aggregations:
        for branch in branches:
            branch_sites = {x[0] for x in branch.required_elements()}
            required_sites.update(branch_sites)
            if branch.properties.title not in aggregations:
                missing_aggregations.append(branch.properties.title)

    response = {
        "aggregations": aggregations,
        "missing_sites": list(required_sites - have_sites),
        "missing_aggr": missing_aggregations,
    }
    return response


def check_title_uniqueness(forest):
    # Legacy, will be removed any decade from now
    # One aggregation cannot be in mutliple groups.
    known_titles: Set[Any] = set()
    for aggrs in forest.values():
        for aggr in aggrs:
            title = aggr["title"]
            if title in known_titles:
                raise MKConfigError(
                    _(
                        'Duplicate BI aggregation with the title "<b>%s</b>". '
                        "Please check your BI configuration and make sure that within each group no aggregation has "
                        "the same title as any other. Note: you can use arguments in the top level "
                        "aggregation rule, like <tt>Host $HOST$</tt>."
                    )
                    % (escaping.escape_attribute(title))
                )
            known_titles.add(title)


def check_aggregation_title_uniqueness(aggregations):
    known_titles: Set[Any] = set()
    for attrs in aggregations.values():
        title = attrs["title"]
        if title in known_titles:
            raise MKConfigError(
                _(
                    'Duplicate BI aggregation with the title "<b>%s</b>". '
                    "Please check your BI configuration and make sure that within each group no aggregation has "
                    "the same title as any other. Note: you can use arguments in the top level "
                    "aggregation rule, like <tt>Host $HOST$</tt>."
                )
                % (escaping.escape_attribute(title))
            )
        known_titles.add(title)


def _get_state_assumption_key(
    site: Any, host: Any, service: Any
) -> Union[Tuple[Any, Any], Tuple[Any, Any, Any]]:
    if service:
        return (site, host, service)
    return (site, host)


@cmk.gui.pages.register("bi_set_assumption")
def ajax_set_assumption() -> None:
    site = request.get_str_input("site")
    host = request.get_str_input("host")
    service = request.get_str_input("service")
    state = request.var("state")
    if state == "none":
        del user.bi_assumptions[_get_state_assumption_key(site, host, service)]
    elif state is not None:
        user.bi_assumptions[_get_state_assumption_key(site, host, service)] = int(state)
    else:
        raise Exception("ajax_set_assumption: state is None")
    user.save_bi_assumptions()


@cmk.gui.pages.register("bi_save_treestate")
def ajax_save_treestate():
    path_id = request.get_str_input_mandatory("path")
    current_ex_level_str, path = path_id.split(":", 1)
    current_ex_level = int(current_ex_level_str)

    if user.bi_expansion_level != current_ex_level:
        user.set_tree_states("bi", {})
    user.set_tree_state("bi", path, request.var("state") == "open")
    user.save_tree_states()

    user.bi_expansion_level = current_ex_level


@cmk.gui.pages.register("bi_render_tree")
def ajax_render_tree():
    aggr_group = request.get_str_input("group")
    aggr_title = request.get_str_input("title")
    omit_root = bool(request.var("omit_root"))
    only_problems = bool(request.var("only_problems"))

    rows = []
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    aggregation_id = request.get_str_input_mandatory("aggregation_id")
    bi_aggregation_filter = BIAggregationFilter(
        [],
        [],
        [aggregation_id],
        [aggr_title] if aggr_title is not None else [],
        [aggr_group] if aggr_group is not None else [],
        [],
    )
    rows = bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)

    # TODO: Cleanup the renderer to use a class registry for lookup
    renderer_class_name = request.var("renderer")
    if renderer_class_name == "FoldableTreeRendererTree":
        renderer_cls: Type[ABCFoldableTreeRenderer] = FoldableTreeRendererTree
    elif renderer_class_name == "FoldableTreeRendererBoxes":
        renderer_cls = FoldableTreeRendererBoxes
    elif renderer_class_name == "FoldableTreeRendererBottomUp":
        renderer_cls = FoldableTreeRendererBottomUp
    elif renderer_class_name == "FoldableTreeRendererTopDown":
        renderer_cls = FoldableTreeRendererTopDown
    else:
        raise NotImplementedError()

    renderer = renderer_cls(
        rows[0],
        omit_root=omit_root,
        expansion_level=user.bi_expansion_level,
        only_problems=only_problems,
        lazy=False,
    )
    html.write_html(renderer.render())


def render_tree_json(row):
    expansion_level = request.get_integer_input_mandatory("expansion_level", 999)

    treestate = user.get_tree_states("bi")
    if expansion_level != user.bi_expansion_level:
        treestate = {}
        user.set_tree_states("bi", treestate)
        user.save_tree_states()

    def render_node_json(tree, show_host):
        is_leaf = len(tree) == 3
        if is_leaf:
            service = tree[2].get("service")
            if not service:
                title = _("Host status")
            else:
                title = service
        else:
            title = tree[2]["title"]

        json_node = {
            "title": title,
            # 2 -> This element is currently in a scheduled downtime
            # 1 -> One of the subelements is in a scheduled downtime
            "in_downtime": tree[0]["in_downtime"],
            "acknowledged": tree[0]["acknowledged"],
            "in_service_period": tree[0]["in_service_period"],
        }

        if is_leaf:
            site, hostname = tree[2]["host"]
            json_node["site"] = site
            json_node["hostname"] = hostname

        # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
        if tree[1] and tree[0] != tree[1]:
            json_node["assumed"] = True
            effective_state = tree[1]
        else:
            json_node["assumed"] = False
            effective_state = tree[0]

        json_node["state"] = effective_state["state"]
        json_node["output"] = compute_output_message(effective_state, tree[2])
        return json_node

    def render_subtree_json(node, path, show_host):
        json_node = render_node_json(node, show_host)

        is_leaf = len(node) == 3
        is_next_level_open = len(path) <= expansion_level

        if not is_leaf and is_next_level_open:
            json_node["nodes"] = []
            for child_node in node[3]:
                if not child_node[2].get("hidden"):
                    new_path = path + [child_node[2]["title"]]
                    json_node["nodes"].append(render_subtree_json(child_node, new_path, show_host))

        return json_node

    root_node = row["aggr_treestate"]
    affected_hosts = row["aggr_hosts"]

    return "", render_subtree_json(root_node, [root_node[2]["title"]], len(affected_hosts) > 1)


def compute_output_message(effective_state, rule):
    output = []
    if effective_state["output"]:
        output.append(effective_state["output"])

    str_state = str(effective_state["state"])
    if str_state in rule.get("state_messages", {}):
        output.append(escaping.escape_attribute(rule["state_messages"][str_state]))
    return ", ".join(output)


# possible aggregated states
MISSING = -2  # currently unused
PENDING = -1
OK = 0
WARN = 1
CRIT = 2
UNKNOWN = 3
UNAVAIL = 4


class ABCFoldableTreeRenderer(abc.ABC):
    def __init__(self, row, omit_root, expansion_level, only_problems, lazy, wrap_texts=True):
        self._row = row
        self._omit_root = omit_root
        self._expansion_level = expansion_level
        self._only_problems = only_problems
        self._lazy = lazy
        self._wrap_texts = wrap_texts
        self._load_tree_state()

    def _load_tree_state(self):
        self._treestate = user.get_tree_states("bi")
        if self._expansion_level != user.bi_expansion_level:
            self._treestate = {}
            user.set_tree_states("bi", self._treestate)
            user.save_tree_states()

    @abc.abstractmethod
    def css_class(self):
        raise NotImplementedError()

    def render(self) -> HTML:
        with output_funnel.plugged():
            self._show_tree()
            return HTML(output_funnel.drain())

    def _show_tree(self):
        tree = self._get_tree()
        affected_hosts = self._row["aggr_hosts"]
        title = self._row["aggr_tree"]["title"]
        group = self._row["aggr_group"]

        url_id = urlencode_vars(
            [
                ("aggregation_id", self._row["aggr_tree"]["aggregation_id"]),
                ("group", group),
                ("title", title),
                ("omit_root", "yes" if self._omit_root else ""),
                ("renderer", self.__class__.__name__),
                ("only_problems", "yes" if self._only_problems else ""),
                ("reqhosts", ",".join("%s#%s" % sitehost for sitehost in affected_hosts)),
            ]
        )

        html.open_div(id_=url_id, class_="bi_tree_container")
        self._show_subtree(tree, path=[tree[2]["title"]], show_host=len(affected_hosts) > 1)
        html.close_div()

    @abc.abstractmethod
    def _show_subtree(self, tree, path, show_host):
        raise NotImplementedError()

    def _get_tree(self):
        tree = self._row["aggr_treestate"]
        if self._only_problems:
            tree = self._filter_tree_only_problems(tree)
        return tree

    # Convert tree to tree contain only node in non-OK state
    def _filter_tree_only_problems(self, tree):
        state, assumed_state, node, subtrees = tree
        # remove subtrees in state OK
        new_subtrees = []
        for subtree in subtrees:
            effective_state = subtree[1] if subtree[1] is not None else subtree[0]
            if effective_state["state"] not in [OK, PENDING]:
                if len(subtree) == 3:
                    new_subtrees.append(subtree)
                else:
                    new_subtrees.append(self._filter_tree_only_problems(subtree))

        return state, assumed_state, node, new_subtrees

    def _is_leaf(self, tree):
        return len(tree) == 3

    def _path_id(self, path):
        return "/".join(path)

    def _is_open(self, path):
        is_open = self._treestate.get(self._path_id(path))
        if is_open is None:
            is_open = len(path) <= self._expansion_level

        # Make sure that in case of BI Boxes (omit root) the root level is *always* visible
        if not is_open and self._omit_root and len(path) == 1:
            is_open = True

        return is_open

    def _omit_content(self, path):
        return self._lazy and not self._is_open(path)

    def _get_mousecode(self, path):
        return "%s(this, %d);" % (self._toggle_js_function(), self._omit_content(path))

    @abc.abstractmethod
    def _toggle_js_function(self):
        raise NotImplementedError()

    def _show_leaf(self, tree, show_host):
        site, host = tree[2]["host"]
        service = tree[2].get("service")

        # Four cases:
        # (1) zbghora17 . Host status   (show_host == True, service is None)
        # (2) zbghora17 . CPU load      (show_host == True, service is not None)
        # (3) Host Status               (show_host == False, service is None)
        # (4) CPU load                  (show_host == False, service is not None)

        if show_host or not service:
            host_url = makeuri_contextless(
                request,
                [("view_name", "hoststatus"), ("site", site), ("host", host)],
                filename="view.py",
            )

        if service:
            service_url = makeuri_contextless(
                request,
                [("view_name", "service"), ("site", site), ("host", host), ("service", service)],
                filename="view.py",
            )

        with self._show_node(tree, show_host):
            self._assume_icon(site, host, service)

            if show_host:
                html.a(host.replace(" ", "&nbsp;"), href=host_url)
                html.b(HTML("&diams;"), class_="bullet")

            if not service:
                html.a(_("Host&nbsp;status"), href=host_url)
            else:
                html.a(service.replace(" ", "&nbsp;"), href=service_url)

    @abc.abstractmethod
    def _show_node(self, tree, show_host, mousecode=None, img_class=None):
        raise NotImplementedError()

    def _assume_icon(self, site, host, service):
        ass = user.bi_assumptions.get(_get_state_assumption_key(site, host, service))
        current_state = str(ass).lower()

        html.icon_button(
            url=None,
            title=_("Assume another state for this item (reload page to activate)"),
            icon="assume_%s" % current_state,
            onclick="cmk.bi.toggle_assumption(this, '%s', '%s', '%s');"
            % (site, host, service.replace("\\", "\\\\") if service else ""),
            cssclass="assumption",
        )

    def _render_bi_state(self, state):
        return {
            PENDING: _("PD"),
            OK: _("OK"),
            WARN: _("WA"),
            CRIT: _("CR"),
            UNKNOWN: _("UN"),
            MISSING: _("MI"),
            UNAVAIL: _("NA"),
        }.get(state, _("??"))


class FoldableTreeRendererTree(ABCFoldableTreeRenderer):
    def css_class(self):
        return "aggrtree"

    def _toggle_js_function(self):
        return "cmk.bi.toggle_subtree"

    def _show_subtree(self, tree, path, show_host):
        if self._is_leaf(tree):
            self._show_leaf(tree, show_host)
            return

        html.open_span(class_="title")

        is_empty = len(tree[3]) == 0
        if is_empty:
            mc = None
        else:
            mc = self._get_mousecode(path)

        css_class = "open" if self._is_open(path) else "closed"

        with self._show_node(tree, show_host, mousecode=mc, img_class=css_class):
            if tree[2].get("icon"):
                html.write_html(html.render_icon(tree[2]["icon"]))
                html.write_text("&nbsp;")

            if tree[2].get("docu_url"):
                html.icon_button(
                    tree[2]["docu_url"],
                    _("Context information about this rule"),
                    "url",
                    target="_blank",
                )
                html.write_text("&nbsp;")

            html.write_text(tree[2]["title"])

        if not is_empty:
            html.open_ul(
                id_="%d:%s" % (self._expansion_level or 0, self._path_id(path)),
                class_=["subtree", css_class],
            )

            if not self._omit_content(path):
                for node in tree[3]:
                    if not node[2].get("hidden"):
                        new_path = path + [node[2]["title"]]
                        html.open_li()
                        self._show_subtree(node, new_path, show_host)
                        html.close_li()

            html.close_ul()

        html.close_span()

    @contextmanager
    def _show_node(self, tree, show_host, mousecode=None, img_class=None):
        # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
        if tree[1] and tree[0] != tree[1]:
            addclass: Optional[str] = "assumed"
            effective_state = tree[1]
        else:
            addclass = None
            effective_state = tree[0]

        class_: List[Optional[str]] = [
            "content",  #
            "state",
            "state%d" % (effective_state["state"] if effective_state["state"] is not None else -1),
            addclass,
        ]
        html.open_span(class_=class_)
        html.write_text(self._render_bi_state(effective_state["state"]))
        html.close_span()

        if mousecode:
            if img_class:
                html.img(
                    src=theme.url("images/tree_closed.svg"),
                    class_=["treeangle", img_class],
                    onclick=mousecode,
                )

            html.open_span(class_=["content", "name"])

        icon_name, icon_title = None, None
        if tree[0]["in_downtime"] == 2:
            icon_name = "downtime"
            icon_title = _("This element is currently in a scheduled downtime.")

        elif tree[0]["in_downtime"] == 1:
            # only display host downtime if the service has no own downtime
            icon_name = "derived_downtime"
            icon_title = _("One of the subelements is in a scheduled downtime.")

        if tree[0]["acknowledged"]:
            icon_name = "ack"
            icon_title = _("This problem has been acknowledged.")

        if not tree[0]["in_service_period"]:
            icon_name = "outof_serviceperiod"
            icon_title = _("This element is currently not in its service period.")

        if icon_name and icon_title:
            html.icon(icon_name, title=icon_title, class_=["icon", "bi"])

        yield

        if mousecode:
            if str(effective_state["state"]) in tree[2].get("state_messages", {}):
                html.b(HTML("&diams;"), class_="bullet")
                html.write_text(tree[2]["state_messages"][str(effective_state["state"])])

            html.close_span()

        output: HTML = cmk.gui.view_utils.format_plugin_output(
            effective_state["output"], shall_escape=config.escape_plugin_output
        )
        if output:
            output = html.render_b(HTML("&diams;"), class_="bullet") + output
        else:
            output = HTML()

        html.span(output, class_=["content", "output"])


class FoldableTreeRendererBoxes(ABCFoldableTreeRenderer):
    def css_class(self):
        return "aggrtree_box"

    def _toggle_js_function(self):
        return "cmk.bi.toggle_box"

    def _show_subtree(self, tree, path, show_host):
        # Check if we have an assumed state: comparing assumed state (tree[1]) with state (tree[0])
        if tree[1] and tree[0] != tree[1]:
            addclass: Optional[str] = "assumed"
            effective_state = tree[1]
        else:
            addclass = None
            effective_state = tree[0]

        is_leaf = self._is_leaf(tree)
        if is_leaf:
            leaf = "leaf"
            mc = None
        else:
            leaf = "noleaf"
            mc = self._get_mousecode(path)

        classes = [
            "bibox_box",
            leaf,
            "open" if self._is_open(path) else "closed",
            "state",
            "state%d" % effective_state["state"],
            addclass,
        ]

        omit = self._omit_root and len(path) == 1
        if not omit:
            html.open_span(
                id_="%d:%s" % (self._expansion_level or 0, self._path_id(path)),
                class_=classes,
                onclick=mc,
            )

            if is_leaf:
                self._show_leaf(tree, show_host)
            else:
                html.write_text(tree[2]["title"].replace(" ", "&nbsp;"))

            html.close_span()

        if not is_leaf and not self._omit_content(path):
            html.open_span(
                class_="bibox",
                style="display: none;" if not self._is_open(path) and not omit else "",
            )
            for node in tree[3]:
                new_path = path + [node[2]["title"]]
                self._show_subtree(node, new_path, show_host)
            html.close_span()

    @contextmanager
    def _show_node(self, tree, show_host, mousecode=None, img_class=None):
        yield

    def _assume_icon(self, site, host, service):
        return  # No assume icon with boxes


class ABCFoldableTreeRendererTable(FoldableTreeRendererTree):
    _mirror = False

    def css_class(self):
        return "aggrtree"

    def _toggle_js_function(self):
        return "cmk.bi.toggle_subtree"

    def _show_tree(self):
        td_style = None if self._wrap_texts == "wrap" else "white-space: nowrap;"

        tree = self._get_tree()
        depth = status_tree_depth(tree)
        leaves = self._gen_table(tree, depth, len(self._row["aggr_hosts"]) > 1)

        html.open_table(class_=["aggrtree", "ltr"])
        odd = "odd"
        for code, colspan, parents in leaves:
            html.open_tr()

            leaf_td = html.render_td(code, class_=["leaf", odd], style=td_style, colspan=colspan)
            odd = "even" if odd == "odd" else "odd"

            tds = [leaf_td]
            for rowspan, c in parents:
                tds.append(html.render_td(c, class_=["node"], style=td_style, rowspan=rowspan))

            if self._mirror:
                tds.reverse()

            html.write_html(HTML("").join(tds))
            html.close_tr()

        html.close_table()

    def _gen_table(self, tree, height, show_host):
        if self._is_leaf(tree):
            return self._gen_leaf(tree, height, show_host)
        return self._gen_node(tree, height, show_host)

    def _gen_leaf(self, tree, height, show_host):
        with output_funnel.plugged():
            self._show_leaf(tree, show_host)
            content = HTML(output_funnel.drain())
        return [(content, height, [])]

    def _gen_node(self, tree, height, show_host):
        leaves: List[Any] = []
        for node in tree[3]:
            if not node[2].get("hidden"):
                leaves += self._gen_table(node, height - 1, show_host)

        with output_funnel.plugged():
            html.open_div(class_="aggr_tree")
            with self._show_node(tree, show_host):
                html.write_text(tree[2]["title"])
            html.close_div()
            content = HTML(output_funnel.drain())

        if leaves:
            leaves[0][2].append((len(leaves), content))

        return leaves


def find_all_leaves(node) -> List[Tuple[Optional[str], HostName, Optional[ServiceName]]]:
    # leaf node
    if node["type"] == 1:
        site, host = node["host"]
        return [(site, host, node.get("service"))]

    # rule node
    if node["type"] == 2:
        entries: List[Any] = []
        for n in node["nodes"]:
            entries += find_all_leaves(n)
        return entries

    # place holders
    return []


def status_tree_depth(tree):
    if len(tree) == 3:
        return 1

    subtrees = tree[3]
    maxdepth = 0
    for node in subtrees:
        maxdepth = max(maxdepth, status_tree_depth(node))
    return maxdepth + 1


class FoldableTreeRendererBottomUp(ABCFoldableTreeRendererTable):
    pass


class FoldableTreeRendererTopDown(ABCFoldableTreeRendererTable):
    _mirror = True


def compute_bi_aggregation_filter(
    context: VisualContext, all_active_filters: Iterable[Filter]
) -> BIAggregationFilter:
    only_hosts = []
    only_group = []
    only_service = []
    only_aggr_name = []
    group_prefix = []

    for active_filter in all_active_filters:
        conf = context.get(active_filter.ident, {})

        if active_filter.ident == "aggr_hosts":
            if (host_name := conf.get("aggr_host_host", "")) != "":
                only_hosts = [host_name]
        elif active_filter.ident == "aggr_group":
            if aggr_group := conf.get(active_filter.htmlvars[0]):
                only_group = [aggr_group]
        elif active_filter.ident == "aggr_service":
            service_spec = tuple(conf.get(var, "") for var in active_filter.htmlvars)
            # service_spec: site_id, host, service
            # Since no data has been fetched yet, the site is also unknown
            if all(service_spec):
                only_service = [(service_spec[1], service_spec[2])]
        elif active_filter.ident == "aggr_name":
            if aggr_name := conf.get("aggr_name"):
                only_aggr_name = [aggr_name]
        elif active_filter.ident == "aggr_group_tree":
            if group_name := conf.get("aggr_group_tree"):
                group_prefix = [group_name]

    # BIAggregationFilter
    # ("hosts", List[HostName]),
    # ("services", List[Tuple[HostName, ServiceName]]),
    # ("aggr_ids", List[str]),
    # ("aggr_names", List[str]),
    # ("aggr_groups", List[str]),
    # ("aggr_paths", List[List[str]]),
    return BIAggregationFilter(
        only_hosts,  # hosts
        only_service,  # services
        [],  # ids
        only_aggr_name,  # names
        only_group,  # groups
        group_prefix,  # paths
    )


def table(
    context: VisualContext,
    columns: List[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: Optional[int],
    all_active_filters: Iterable[Filter],
) -> List[Dict]:
    bi_aggregation_filter = compute_bi_aggregation_filter(context, all_active_filters)
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    return bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)


def hostname_table(view, columns, query, only_sites, limit, all_active_filters):
    """Table of all host aggregations, i.e. aggregations using data from exactly one host"""
    return singlehost_table(
        view, columns, query, only_sites, limit, all_active_filters, joinbyname=True, bygroup=False
    )


def hostname_by_group_table(view, columns, query, only_sites, limit, all_active_filters):
    return singlehost_table(
        view, columns, query, only_sites, limit, all_active_filters, joinbyname=True, bygroup=True
    )


def host_table(view, columns, query, only_sites, limit, all_active_filters):
    return singlehost_table(
        view, columns, query, only_sites, limit, all_active_filters, joinbyname=False, bygroup=False
    )


def singlehost_table(
    view, columns, query, only_sites, limit, all_active_filters, joinbyname, bygroup
):

    filterheaders = "".join(get_livestatus_filter_headers(view.context, all_active_filters))
    host_columns = [c for c in columns if c.startswith("host_")]

    rows = []
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    bi_aggregation_filter = compute_bi_aggregation_filter(view.context, all_active_filters)
    required_aggregations = bi_manager.computer.get_required_aggregations(bi_aggregation_filter)
    bi_manager.status_fetcher.update_states_filtered(
        filterheaders, only_sites, limit, host_columns, bygroup, required_aggregations
    )

    aggregation_results = bi_manager.computer.compute_results(required_aggregations)
    legacy_results = bi_manager.computer.convert_to_legacy_results(
        aggregation_results, bi_aggregation_filter
    )

    for site_host_name, values in bi_manager.status_fetcher.states.items():
        for legacy_result in legacy_results:
            if site_host_name in legacy_result["aggr_hosts"]:
                # Combine bi columns + extra livestatus columns + bi computation columns into one row
                row = values._asdict()
                row.update(row["remaining_row_keys"])
                del row["remaining_row_keys"]
                row.update(legacy_result)
                row["site"] = site_host_name[0]
                rows.append(row)
    return rows


class BIManager:
    def __init__(self):
        sites_callback = SitesCallback(cmk.gui.sites.states, bi_livestatus_query)
        self.compiler = BICompiler(self.bi_configuration_file(), sites_callback)
        self.compiler.load_compiled_aggregations()
        self.status_fetcher = BIStatusFetcher(sites_callback)
        self.computer = BIComputer(self.compiler.compiled_aggregations, self.status_fetcher)

    @classmethod
    def bi_configuration_file(cls) -> str:
        return str(Path(watolib.multisite_dir()) / "bi_config.bi")


@request_memoize()
def get_cached_bi_packs() -> BIAggregationPacks:
    bi_packs = BIAggregationPacks(BIManager.bi_configuration_file())
    bi_packs.load_config()
    return bi_packs


@request_memoize()
def get_cached_bi_manager() -> BIManager:
    return BIManager()


@request_memoize()
def get_cached_bi_compiler() -> BICompiler:
    return BICompiler(
        BIManager.bi_configuration_file(), SitesCallback(cmk.gui.sites.states, bi_livestatus_query)
    )


def bi_livestatus_query(
    query: str,
    only_sites: Optional[List[SiteId]] = None,
    output_format: LivestatusOutputFormat = LivestatusOutputFormat.PYTHON,
) -> LivestatusResponse:

    with sites.output_format(output_format), sites.only_sites(only_sites), sites.prepend_site():
        try:
            sites.live().set_auth_domain("bi")
            return sites.live().query(query)
        finally:
            sites.live().set_auth_domain("read")
