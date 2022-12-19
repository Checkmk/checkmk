#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from typing import Any

from livestatus import OnlySites

from cmk.utils.defines import short_service_state_name

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.plugins.visuals.utils import Filter, get_livestatus_filter_headers
from cmk.gui.type_defs import ColumnName, Row, Rows, SingleInfos, VisualContext
from cmk.gui.utils.escaping import escape_attribute
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri, urlencode_vars
from cmk.gui.valuespec import DropdownChoice, ValueSpec
from cmk.gui.views.data_source import ABCDataSource, RowTable
from cmk.gui.views.painter.v0.base import Cell, CellSpec, CSVExportError, Painter
from cmk.gui.views.painter_options import PainterOption, PainterOptions

from cmk.bi.computer import BIAggregationFilter

from .bi_manager import BIManager
from .foldable_tree_renderer import (
    ABCFoldableTreeRenderer,
    FoldableTreeRendererBottomUp,
    FoldableTreeRendererBoxes,
    FoldableTreeRendererTopDown,
    FoldableTreeRendererTree,
)

#     ____        _
#    |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___
#    | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#    | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#    |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#


class DataSourceBIAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_aggregations"

    @property
    def title(self) -> str:
        return _("BI Aggregations")

    @property
    def table(self) -> RowTable:
        return RowTableBIAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "aggr_group"]

    @property
    def unsupported_columns(self) -> list[ColumnName]:
        return ["site"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIAggregations(RowTable):
    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: int | None,
        all_active_filters: list[Filter],
    ) -> Rows | tuple[Rows, int]:
        return table(context, columns, headers, only_sites, limit, all_active_filters)


class DataSourceBIHostAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_host_aggregations"

    @property
    def title(self) -> str:
        return _("BI Aggregations affected by one host")

    @property
    def table(self) -> RowTable:
        return RowTableBIHostAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostAggregations(RowTable):
    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: int | None,
        all_active_filters: list[Filter],
    ) -> Rows | tuple[Rows, int]:
        return host_table(context, columns, headers, only_sites, limit, all_active_filters)


class DataSourceBIHostnameAggregations(ABCDataSource):
    """Similar to host aggregations, but the name of the aggregation
    is used to join the host table rather then the affected host"""

    @property
    def ident(self) -> str:
        return "bi_hostname_aggregations"

    @property
    def title(self) -> str:
        return _("BI Hostname Aggregations")

    @property
    def table(self) -> RowTable:
        return RowTableBIHostnameAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostnameAggregations(RowTable):
    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: int | None,
        all_active_filters: list[Filter],
    ) -> Rows | tuple[Rows, int]:
        return hostname_table(context, columns, headers, only_sites, limit, all_active_filters)


class DataSourceBIHostnameByGroupAggregations(ABCDataSource):
    """The same but with group information"""

    @property
    def ident(self) -> str:
        return "bi_hostnamebygroup_aggregations"

    @property
    def title(self) -> str:
        return _("BI aggregations for hosts by host groups")

    @property
    def table(self) -> RowTable:
        return RowTableBIHostnameByGroupAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "hostgroup", "aggr_group"]

    @property
    def keys(self) -> list[ColumnName]:
        return []

    @property
    def id_keys(self) -> list[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostnameByGroupAggregations(RowTable):
    def query(
        self,
        datasource: ABCDataSource,
        cells: Sequence[Cell],
        columns: list[ColumnName],
        context: VisualContext,
        headers: str,
        only_sites: OnlySites,
        limit: int | None,
        all_active_filters: list[Filter],
    ) -> Rows | tuple[Rows, int]:
        return hostname_by_group_table(
            context, columns, headers, only_sites, limit, all_active_filters
        )


def table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> list[dict]:
    bi_aggregation_filter = compute_bi_aggregation_filter(context, all_active_filters)
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    return bi_manager.computer.compute_legacy_result_for_filter(bi_aggregation_filter)


def hostname_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> Rows:
    """Table of all host aggregations, i.e. aggregations using data from exactly one host"""
    return singlehost_table(
        context,
        columns,
        query,
        only_sites,
        limit,
        all_active_filters,
        joinbyname=True,
        bygroup=False,
    )


def hostname_by_group_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> Rows:
    return singlehost_table(
        context,
        columns,
        query,
        only_sites,
        limit,
        all_active_filters,
        joinbyname=True,
        bygroup=True,
    )


def host_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
) -> Rows:
    return singlehost_table(
        context,
        columns,
        query,
        only_sites,
        limit,
        all_active_filters,
        joinbyname=False,
        bygroup=False,
    )


def singlehost_table(
    context: VisualContext,
    columns: list[ColumnName],
    query: str,
    only_sites: OnlySites,
    limit: int | None,
    all_active_filters: Iterable[Filter],
    joinbyname: bool,
    bygroup: bool,
) -> Rows:
    filterheaders = "".join(get_livestatus_filter_headers(context, all_active_filters))
    host_columns = [c for c in columns if c.startswith("host_")]

    rows = []
    bi_manager = BIManager()
    bi_manager.status_fetcher.set_assumed_states(user.bi_assumptions)
    bi_aggregation_filter = compute_bi_aggregation_filter(context, all_active_filters)
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


#     ____       _       _
#    |  _ \ __ _(_)_ __ | |_ ___ _ __ ___
#    | |_) / _` | | '_ \| __/ _ \ '__/ __|
#    |  __/ (_| | | | | | ||  __/ |  \__ \
#    |_|   \__,_|_|_| |_|\__\___|_|  |___/
#


class PainterAggrIcons(Painter):
    @property
    def ident(self) -> str:
        return "aggr_icons"

    def title(self, cell):
        return _("Links")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_group", "aggr_name", "aggr_effective_state"]

    @property
    def printable(self):
        return False

    def render(self, row: Row, cell: Cell) -> CellSpec:
        single_url = "view.py?" + urlencode_vars(
            [("view_name", "aggr_single"), ("aggr_name", row["aggr_name"])]
        )
        avail_url = single_url + "&mode=availability"

        bi_map_url = "bi_map.py?" + urlencode_vars(
            [
                ("aggr_name", row["aggr_name"]),
            ]
        )

        with output_funnel.plugged():
            html.icon_button(bi_map_url, _("Visualize this aggregation"), "aggr")
            html.icon_button(single_url, _("Show only this aggregation"), "showbi")
            html.icon_button(
                avail_url, _("Analyse availability of this aggregation"), "availability"
            )
            if row["aggr_effective_state"]["in_downtime"] != 0:
                html.icon(
                    "derived_downtime", _("A service or host in this aggregation is in downtime.")
                )
            if row["aggr_effective_state"]["acknowledged"]:
                html.icon(
                    "ack",
                    _(
                        "The critical problems that make this aggregation non-OK have been acknowledged."
                    ),
                )
            if not row["aggr_effective_state"]["in_service_period"]:
                html.icon(
                    "outof_serviceperiod",
                    _("This aggregation is currently out of its service period."),
                )
            code = HTML(output_funnel.drain())
        return "buttons", code


class PainterAggrInDowntime(Painter):
    @property
    def ident(self) -> str:
        return "aggr_in_downtime"

    def title(self, cell):
        return _("In Downtime")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", (row["aggr_effective_state"]["in_downtime"] and "1" or "0"))


class PainterAggrAcknowledged(Painter):
    @property
    def ident(self) -> str:
        return "aggr_acknowledged"

    def title(self, cell):
        return _("Acknowledged")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", (row["aggr_effective_state"]["acknowledged"] and "1" or "0"))


def _paint_aggr_state_short(state, assumed=False):
    if state is None:
        return "", ""
    name = short_service_state_name(state["state"], "")
    classes = "state svcstate state%s" % state["state"]
    if assumed:
        classes += " assumed"
    return classes, HTMLWriter.render_span(name, class_=["state_rounded_fill"])


class PainterAggrState(Painter):
    @property
    def ident(self) -> str:
        return "aggr_state"

    def title(self, cell):
        return _("Aggregated state")

    def short_title(self, cell):
        return _("State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_aggr_state_short(
            row["aggr_effective_state"], row["aggr_effective_state"] != row["aggr_state"]
        )


class PainterAggrStateNum(Painter):
    @property
    def ident(self) -> str:
        return "aggr_state_num"

    def title(self, cell):
        return _("Aggregated state (number)")

    def short_title(self, cell):
        return _("State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", str(row["aggr_effective_state"]["state"]))


class PainterAggrRealState(Painter):
    @property
    def ident(self) -> str:
        return "aggr_real_state"

    def title(self, cell):
        return _("Aggregated real state (never assumed)")

    def short_title(self, cell):
        return _("R.State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_aggr_state_short(row["aggr_state"])


class PainterAggrAssumedState(Painter):
    @property
    def ident(self) -> str:
        return "aggr_assumed_state"

    def title(self, cell):
        return _("Aggregated assumed state")

    def short_title(self, cell):
        return _("Assumed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_assumed_state"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return _paint_aggr_state_short(row["aggr_assumed_state"])


class PainterAggrGroup(Painter):
    @property
    def ident(self) -> str:
        return "aggr_group"

    def title(self, cell):
        return _("Aggregation group")

    def short_title(self, cell):
        return _("Group")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_group"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return "", escape_attribute(row["aggr_group"])


class PainterAggrName(Painter):
    @property
    def ident(self) -> str:
        return "aggr_name"

    def title(self, cell):
        return _("Aggregation name")

    def short_title(self, cell):
        return _("Aggregation")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_name"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return "", escape_attribute(row["aggr_name"])


class PainterAggrOutput(Painter):
    @property
    def ident(self) -> str:
        return "aggr_output"

    def title(self, cell):
        return _("Aggregation status output")

    def short_title(self, cell):
        return _("Output")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_output"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return ("", row["aggr_output"])


def paint_aggr_hosts(row, link_to_view):
    h = []
    for site, host in row["aggr_hosts"]:
        url = makeuri(request, [("view_name", link_to_view), ("site", site), ("host", host)])
        h.append(HTMLWriter.render_a(host, url))
    return "", HTML(" ").join(h)


class PainterAggrHosts(Painter):
    @property
    def ident(self) -> str:
        return "aggr_hosts"

    def title(self, cell):
        return _("Aggregation: affected hosts")

    def short_title(self, cell):
        return _("Hosts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_hosts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_aggr_hosts(row, "aggr_host")


class PainterAggrHostsServices(Painter):
    @property
    def ident(self) -> str:
        return "aggr_hosts_services"

    def title(self, cell):
        return _("Aggregation: affected hosts (link to host page)")

    def short_title(self, cell):
        return _("Hosts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_hosts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_aggr_hosts(row, "host")


class PainterOptionAggrExpand(PainterOption):
    @property
    def ident(self) -> str:
        return "aggr_expand"

    @property
    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Initial expansion of aggregations"),
            default_value="0",
            choices=[
                ("0", _("collapsed")),
                ("1", _("first level")),
                ("2", _("two levels")),
                ("3", _("three levels")),
                ("999", _("complete")),
            ],
        )


class PainterOptionAggrOnlyProblems(PainterOption):
    @property
    def ident(self) -> str:
        return "aggr_onlyproblems"

    @property
    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Show only problems"),
            default_value="0",
            choices=[
                ("0", _("show all")),
                ("1", _("show only problems")),
            ],
        )


class PainterOptionAggrTreeType(PainterOption):
    @property
    def ident(self) -> str:
        return "aggr_treetype"

    @property
    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Type of tree layout"),
            default_value="foldable",
            choices=[
                ("foldable", _("Foldable tree")),
                ("boxes", _("Boxes")),
                ("boxes-omit-root", _("Boxes (omit root)")),
                ("bottom-up", _("Table: bottom up")),
                ("top-down", _("Table: top down")),
            ],
        )


class PainterOptionAggrWrap(PainterOption):
    @property
    def ident(self) -> str:
        return "aggr_wrap"

    @property
    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Handling of too long texts (affects only table)"),
            default_value="wrap",
            choices=[
                ("wrap", _("wrap")),
                ("nowrap", _("don't wrap")),
            ],
        )


def paint_aggregated_tree_state(
    row: Row, force_renderer_cls: type[ABCFoldableTreeRenderer] | None = None
) -> CellSpec:
    painter_options = PainterOptions.get_instance()
    treetype = painter_options.get("aggr_treetype")
    expansion_level = int(painter_options.get("aggr_expand"))
    only_problems = painter_options.get("aggr_onlyproblems") == "1"
    wrap_texts = painter_options.get("aggr_wrap")

    if force_renderer_cls:
        cls = force_renderer_cls
    elif treetype == "foldable":
        cls = FoldableTreeRendererTree
    elif treetype in ["boxes", "boxes-omit-root"]:
        cls = FoldableTreeRendererBoxes
    elif treetype == "bottom-up":
        cls = FoldableTreeRendererBottomUp
    elif treetype == "top-down":
        cls = FoldableTreeRendererTopDown
    else:
        raise NotImplementedError()

    renderer = cls(
        row,
        omit_root=(treetype == "boxes-omit-root"),
        expansion_level=expansion_level,
        only_problems=only_problems,
        lazy=True,
        wrap_texts=wrap_texts,
    )
    return renderer.css_class(), renderer.render()


class PainterAggrTreestate(Painter):
    @property
    def ident(self) -> str:
        return "aggr_treestate"

    def title(self, cell):
        return _("Aggregation: complete tree")

    def short_title(self, cell):
        return _("Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_treestate", "aggr_hosts"]

    @property
    def painter_options(self):
        return ["aggr_expand", "aggr_onlyproblems", "aggr_treetype", "aggr_wrap"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_aggregated_tree_state(row)

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> dict:
        return render_tree_json(row)


class PainterAggrTreestateBoxed(Painter):
    @property
    def ident(self) -> str:
        return "aggr_treestate_boxed"

    def title(self, cell):
        return _("Aggregation: simplistic boxed layout")

    def short_title(self, cell):
        return _("Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_treestate", "aggr_hosts"]

    def render(self, row: Row, cell: Cell) -> CellSpec:
        return paint_aggregated_tree_state(row, force_renderer_cls=FoldableTreeRendererBoxes)

    def export_for_csv(self, row: Row, cell: Cell) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell) -> dict:
        return render_tree_json(row)


def render_tree_json(row) -> dict[str, Any]:  # type:ignore[no-untyped-def]
    expansion_level = request.get_integer_input_mandatory("expansion_level", 999)

    treestate = user.get_tree_states("bi")
    if expansion_level != user.bi_expansion_level:
        treestate = {}
        user.set_tree_states("bi", treestate)
        user.save_tree_states()

    def render_node_json(tree, show_host) -> dict[str, Any]:  # type:ignore[no-untyped-def]
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

    def render_subtree_json(node, path, show_host) -> dict[str, Any]:  # type:ignore[no-untyped-def]
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

    return render_subtree_json(root_node, [root_node[2]["title"]], len(affected_hosts) > 1)


def compute_output_message(effective_state, rule):
    output = []
    if effective_state["output"]:
        output.append(effective_state["output"])

    str_state = str(effective_state["state"])
    if str_state in rule.get("state_messages", {}):
        output.append(escape_attribute(rule["state_messages"][str_state]))
    return ", ".join(output)
