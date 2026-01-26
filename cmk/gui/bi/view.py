#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"

import typing
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Literal

from livestatus import OnlySites

from cmk.bi import storage
from cmk.bi.computer import BIAggregationFilter
from cmk.bi.filesystem import get_default_site_filesystem
from cmk.bi.lib import FrozenMarker
from cmk.bi.trees import BICompiledRule
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.bi.bi_manager import BIManager, load_compiled_branch
from cmk.gui.bi.foldable_tree_renderer import (
    ABCFoldableTreeRenderer,
    BIAggrTreeState,
    BILeafTreeState,
    FoldableTreeRendererBottomUp,
    FoldableTreeRendererBoxes,
    FoldableTreeRendererTopDown,
    FoldableTreeRendererTree,
    is_aggr,
)
from cmk.gui.data_source import ABCDataSource, RowTable
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import Request, request
from cmk.gui.i18n import _, _l, ungettext
from cmk.gui.logged_in import LoggedInSuperUser, LoggedInUser, user
from cmk.gui.painter.v0 import Cell, Painter
from cmk.gui.painter_options import PainterOption, PainterOptions
from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.type_defs import (
    ColumnName,
    DynamicIconName,
    IconNames,
    Row,
    Rows,
    SingleInfos,
    StaticIcon,
    VisualContext,
)
from cmk.gui.utils.escaping import escape_attribute
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri, urlencode_vars
from cmk.gui.valuespec import DropdownChoice
from cmk.gui.view_utils import CellSpec, CSVExportError
from cmk.gui.views.command import (
    Command,
    CommandActionResult,
    CommandGroup,
    CommandSpec,
    PERMISSION_SECTION_ACTION,
)
from cmk.gui.visuals import get_livestatus_filter_headers
from cmk.gui.visuals.filter import Filter
from cmk.livestatus_client import Dummy
from cmk.utils.servicename import ServiceName
from cmk.utils.statename import short_service_state_name


class DataSourceBIAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_aggregations"

    @property
    def title(self) -> str:
        return _("BI aggregations")

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
        return _("BI host name aggregations")

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
    only_hosts: list[HostName] = []
    only_group = []
    only_service: list[tuple[HostName, ServiceName]] = []
    only_aggr_name = []
    group_prefix = []

    for active_filter in all_active_filters:
        conf = context.get(active_filter.ident, {})

        if active_filter.ident == "aggr_hosts":
            if (host_name := HostName(conf.get("aggr_host_host", ""))) != HostName(""):
                only_hosts = [host_name]
        elif active_filter.ident == "aggr_group":
            if aggr_group := conf.get(active_filter.htmlvars[0]):
                only_group = [aggr_group]
        elif active_filter.ident == "aggr_service":
            service_spec = tuple(conf.get(var, "") for var in active_filter.htmlvars)
            # service_spec: site_id, host, service
            # Since no data has been fetched yet, the site is also unknown
            if all(service_spec):
                only_service = [(HostName(service_spec[1]), service_spec[2])]
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

    def title(self, cell: Cell) -> str:
        return _("Links")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_group", "aggr_name", "aggr_effective_state", "aggr_compiled_aggregation"]

    @property
    def printable(self) -> bool:
        return False

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        single_url = "view.py?" + urlencode_vars(
            [("view_name", "aggr_single"), ("aggr_name", row["aggr_name"])]
        )
        avail_url = single_url + "&mode=availability"

        bi_map_url = "bi_map.py?" + urlencode_vars(
            [
                ("aggr_name", row["aggr_name"]),
            ]
        )

        bi_frozen_diff_url = "view.py?" + urlencode_vars(
            [("aggr_name", row["aggr_name"]), ("view_name", "aggr_frozen_diff")]
        )

        frozen_info = row["aggr_compiled_aggregation"].frozen_info
        with output_funnel.plugged():
            if frozen_info is not None:
                compiled_branch = load_compiled_branch(
                    frozen_info.based_on_aggregation_id, frozen_info.based_on_branch_title
                )
                frozen_elements = row["aggr_compiled_aggregation"].branches[0].required_elements()
                live_elements = compiled_branch.required_elements()
                if frozen_elements.symmetric_difference(live_elements):
                    html.icon_button(
                        bi_frozen_diff_url,
                        _("This aggregation is frozen. The live version has changes."),
                        StaticIcon(
                            IconNames.bi_freeze,
                            emblem="warning",
                        ),
                    )
                else:
                    html.icon_button(
                        bi_frozen_diff_url,
                        _("This aggregation is frozen"),
                        StaticIcon(IconNames.bi_freeze),
                    )
            html.icon_button(
                bi_map_url, _("Visualize this aggregation"), StaticIcon(IconNames.aggr)
            )
            html.icon_button(
                single_url, _("Show only this aggregation"), StaticIcon(IconNames.showbi)
            )
            html.icon_button(
                avail_url,
                _("Analyse availability of this aggregation"),
                StaticIcon(IconNames.availability),
            )
            if row["aggr_effective_state"]["in_downtime"] != 0:
                html.static_icon(
                    StaticIcon(IconNames.downtime),
                    title=_("A service or host in this aggregation is in downtime."),
                )
            if row["aggr_effective_state"]["acknowledged"]:
                html.static_icon(
                    StaticIcon(IconNames.ack),
                    title=_(
                        "The critical problems that make this aggregation non-OK have been acknowledged."
                    ),
                )
            if not row["aggr_effective_state"]["in_service_period"]:
                html.static_icon(
                    StaticIcon(IconNames.outof_serviceperiod),
                    title=_("This aggregation is currently out of its service period."),
                )
            code = HTML.without_escaping(output_funnel.drain())
        return "buttons", code


class PainterAggrInDowntime(Painter):
    @property
    def ident(self) -> str:
        return "aggr_in_downtime"

    def title(self, cell: Cell) -> str:
        return _("In Downtime")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", (row["aggr_effective_state"]["in_downtime"] and "1" or "0"))


class PainterAggrAcknowledged(Painter):
    @property
    def ident(self) -> str:
        return "aggr_acknowledged"

    def title(self, cell: Cell) -> str:
        return _("Acknowledged")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", (row["aggr_effective_state"]["acknowledged"] and "1" or "0"))


def _paint_aggr_state_short(
    state: dict[str, Any] | None, assumed: bool = False
) -> tuple[str, str | HTML]:
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

    def title(self, cell: Cell) -> str:
        return _("Aggregated state")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_aggr_state_short(
            row["aggr_effective_state"], row["aggr_effective_state"] != row["aggr_state"]
        )


class PainterAggrStateNum(Painter):
    @property
    def ident(self) -> str:
        return "aggr_state_num"

    def title(self, cell: Cell) -> str:
        return _("Aggregated state (number)")

    def short_title(self, cell: Cell) -> str:
        return _("State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_effective_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", str(row["aggr_effective_state"]["state"]))


class PainterAggrRealState(Painter):
    @property
    def ident(self) -> str:
        return "aggr_real_state"

    def title(self, cell: Cell) -> str:
        return _("Aggregated real state (never assumed)")

    def short_title(self, cell: Cell) -> str:
        return _("R.State")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_aggr_state_short(row["aggr_state"])


class PainterAggrAssumedState(Painter):
    @property
    def ident(self) -> str:
        return "aggr_assumed_state"

    def title(self, cell: Cell) -> str:
        return _("Aggregated assumed state")

    def short_title(self, cell: Cell) -> str:
        return _("Assumed")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_assumed_state"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return _paint_aggr_state_short(row["aggr_assumed_state"])


class PainterAggrGroup(Painter):
    @property
    def ident(self) -> str:
        return "aggr_group"

    def title(self, cell: Cell) -> str:
        return _("Aggregation group")

    def short_title(self, cell: Cell) -> str:
        return _("Group")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_group"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return "", HTML.with_escaping(row["aggr_group"])


class PainterAggrName(Painter):
    @property
    def ident(self) -> str:
        return "aggr_name"

    def title(self, cell: Cell) -> str:
        return _("Aggregation name")

    def short_title(self, cell: Cell) -> str:
        return _("Aggregation")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_name"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return "", escape_attribute(row["aggr_name"])


class PainterAggrOutput(Painter):
    @property
    def ident(self) -> str:
        return "aggr_output"

    def title(self, cell: Cell) -> str:
        return _("Aggregation status output")

    def short_title(self, cell: Cell) -> str:
        return _("Output")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_output"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return ("", row["aggr_output"])


def paint_aggr_hosts(
    row: Row,
    link_to_view: str,
    *,
    request: Request,
) -> CellSpec:
    h = []
    for site, host in row["aggr_hosts"]:
        url = makeuri(request, [("view_name", link_to_view), ("site", site), ("host", host)])
        h.append(HTMLWriter.render_a(host, url))
    return "", HTML.without_escaping(" ").join(h)


class PainterAggrHosts(Painter):
    @property
    def ident(self) -> str:
        return "aggr_hosts"

    def title(self, cell: Cell) -> str:
        return _("Aggregation: affected hosts")

    def short_title(self, cell: Cell) -> str:
        return _("Hosts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_hosts"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_aggr_hosts(row, "aggr_host", request=self.request)


class PainterAggrHostsServices(Painter):
    @property
    def ident(self) -> str:
        return "aggr_hosts_services"

    def title(self, cell: Cell) -> str:
        return _("Aggregation: affected hosts (link to host page)")

    def short_title(self, cell: Cell) -> str:
        return _("Hosts")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_hosts"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_aggr_hosts(row, "host", request=self.request)


class PainterOptionAggrExpand(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="aggr_expand",
            valuespec=DropdownChoice(
                title=_("Initial expansion of aggregations"),
                default_value="0",
                choices=[
                    ("0", _("collapsed")),
                    ("1", _("first level")),
                    ("2", _("two levels")),
                    ("3", _("three levels")),
                    ("999", _("complete")),
                ],
            ),
        )


class PainterOptionAggrOnlyProblems(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="aggr_onlyproblems",
            valuespec=DropdownChoice(
                title=_("Show only problems"),
                default_value="0",
                choices=[
                    ("0", _("show all")),
                    ("1", _("show only problems")),
                ],
            ),
        )


class PainterOptionAggrTreeType(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="aggr_treetype",
            valuespec=DropdownChoice(
                title=_("Type of tree layout"),
                default_value="foldable",
                choices=[
                    ("foldable", _("Foldable tree")),
                    ("boxes", _("Boxes")),
                    ("boxes-omit-root", _("Boxes (omit root)")),
                    ("bottom-up", _("Table: bottom up")),
                    ("top-down", _("Table: top down")),
                ],
            ),
        )


class PainterOptionAggrWrap(PainterOption):
    def __init__(self) -> None:
        super().__init__(
            ident="aggr_wrap",
            valuespec=DropdownChoice(
                title=_("Handling of too long texts (affects only table)"),
                default_value="wrap",
                choices=[
                    ("wrap", _("wrap")),
                    ("nowrap", _("don't wrap")),
                ],
            ),
        )


def paint_aggregated_tree_state(
    row: Row,
    *,
    painter_options: PainterOptions,
    force_renderer_cls: type[ABCFoldableTreeRenderer] | None = None,
    show_frozen_difference: bool = False,
) -> CellSpec:
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

    if show_frozen_difference and row["aggr_compiled_aggregation"].frozen_info:
        row, aggregations_are_equal = convert_tree_to_frozen_diff_tree(row)
        if aggregations_are_equal:
            return "", _("Aggregations are equal")

    renderer = cls(
        row,
        omit_root=(treetype == "boxes-omit-root"),
        expansion_level=expansion_level,
        only_problems=only_problems,
        lazy=True,
        wrap_texts=wrap_texts,
        show_frozen_difference=show_frozen_difference,
    )
    return renderer.css_class(), renderer.render()


class PainterAggrTreestate(Painter):
    @property
    def ident(self) -> str:
        return "aggr_treestate"

    def title(self, cell: Cell) -> str:
        return _("Complete tree")

    def short_title(self, cell: Cell) -> str:
        return _("Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_treestate", "aggr_hosts"]

    @property
    def painter_options(self) -> list[str]:
        return ["aggr_expand", "aggr_onlyproblems", "aggr_treetype", "aggr_wrap"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_aggregated_tree_state(row, painter_options=self._painter_options)

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> dict:
        return render_tree_json(row, user=user, request=self.request)

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> dict:
        return render_tree_json(row, user=user, request=self.request)


class PainterAggrTreestateFrozenDiff(Painter):
    @property
    def ident(self) -> str:
        return "aggr_treestate_frozen_diff"

    def title(self, cell: Cell) -> str:
        return _("Difference between frozen and live aggregation")

    def short_title(self, cell: Cell) -> str:
        return _("Difference between frozen and live aggregation")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_treestate", "aggr_hosts", "aggr_compiled_aggregation"]

    @property
    def painter_options(self) -> list[str]:
        return ["aggr_expand", "aggr_onlyproblems", "aggr_treetype", "aggr_wrap"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        frozen_info = row["aggr_compiled_aggregation"].frozen_info
        if frozen_info is None:
            return "", _("Aggregation not configured to be frozen")

        return paint_aggregated_tree_state(
            row, painter_options=self._painter_options, show_frozen_difference=True
        )

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> dict:
        return render_tree_json(row, user=user, request=self.request)

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> dict:
        return render_tree_json(row, user=user, request=self.request)


@request_memoize()
def _get_cached_bi_manager() -> BIManager:
    return BIManager()


def convert_tree_to_frozen_diff_tree(row: Row) -> tuple[Row, bool]:
    reference_name = row["aggr_id"]
    frozen_info = row["aggr_compiled_aggregation"].frozen_info

    original_aggr_group = row["aggr_group"]
    other_aggregation = frozen_info.based_on_aggregation_id
    other_branch = frozen_info.based_on_branch_title
    bi_manager = _get_cached_bi_manager()
    found_aggr = bi_manager.compiler.get_aggregation_by_name(reference_name)
    if not found_aggr:
        raise MKGeneralException("Unable to find source aggregation for diff tree")
    bi_ref_aggregation, bi_ref_branch = found_aggr

    # Load other aggregation from disk
    other_aggr = storage.AggregationStore(get_default_site_filesystem().cache).get(
        other_aggregation
    )

    aggregations_are_equal = True
    for bi_other_branch in other_aggr.branches:
        if bi_other_branch.properties.title == other_branch:
            aggregations_are_equal = combine_branches(bi_ref_branch, bi_other_branch)

    required_aggregations = [(bi_ref_aggregation, [bi_ref_branch])]
    required_elements = bi_manager.computer.get_required_elements(required_aggregations)
    bi_manager.status_fetcher.update_states(required_elements)
    result = bi_manager.computer.compute_results(required_aggregations)
    row = bi_ref_aggregation.convert_result_to_legacy_format(result[0][1][0])
    row["aggr_group"] = original_aggr_group
    return row, aggregations_are_equal


def combine_branches(reference_branch: BICompiledRule, other_branch: BICompiledRule) -> bool:
    """Modifies the reference branch inline, returns true/false if the branches are equal"""
    ref_idents = reference_branch.get_identifiers((), set())
    other_idents = other_branch.get_identifiers((), set())

    ref_ids = {x.id: x.node_ref for x in ref_idents}
    other_ids = {x.id: x.node_ref for x in other_idents}

    if set(ref_ids) == set(other_ids):
        return True

    # Iterate over reference branch, mark missing elements
    for missing_id in set(ref_ids) - set(other_ids):
        # TODO: check if it wasn't shifted to another number
        #    - detect sub-index where the missing part starts
        #    - iterate available other_ident numbers for this sub-idx
        #    - check for matches
        #    will be implemented once the graphical representation is complete, easier to debug
        #        html.debug("set missing", missing_id)
        ref_ids[missing_id].set_frozen_marker(FrozenMarker("missing"))

    def common_prefix(
        check_tuple: tuple[int | str, ...], other_tuples: set[tuple[int | str, ...]]
    ) -> tuple[int | str, ...] | None:
        while len(check_tuple) > 0:
            if check_tuple in other_tuples:
                return check_tuple
            check_tuple = check_tuple[:-1]
        return None

    mod_idents = reference_branch.get_identifiers((), set())
    mod_ids = {x.id: x.node_ref for x in mod_idents}

    for new_id in set(other_ids) - set(ref_ids):
        other_ids[new_id].set_frozen_marker(FrozenMarker("new"))
        if new_id in mod_ids:
            continue
        prefix = common_prefix(new_id, set(ref_ids))

        insert_location = ref_ids[prefix]  # type: ignore[index]
        nodes_to_insert = other_ids[new_id[: len(prefix) + 1]]  # type: ignore[arg-type]
        assert isinstance(insert_location, BICompiledRule)
        insert_location.nodes.append(nodes_to_insert)
        mod_idents = reference_branch.get_identifiers((), set())
        mod_ids = {x.id: x.node_ref for x in mod_idents}

    return False


class PainterAggrTreestateBoxed(Painter):
    @property
    def ident(self) -> str:
        return "aggr_treestate_boxed"

    def title(self, cell: Cell) -> str:
        return _("Aggregation: simplistic boxed layout")

    def short_title(self, cell: Cell) -> str:
        return _("Tree")

    @property
    def columns(self) -> Sequence[ColumnName]:
        return ["aggr_treestate", "aggr_hosts"]

    def render(self, row: Row, cell: Cell, user: LoggedInUser) -> CellSpec:
        return paint_aggregated_tree_state(
            row,
            painter_options=self._painter_options,
            force_renderer_cls=FoldableTreeRendererBoxes,
        )

    def export_for_python(self, row: Row, cell: Cell, user: LoggedInUser) -> dict:
        return render_tree_json(row, user=user, request=self.request)

    def export_for_csv(self, row: Row, cell: Cell, user: LoggedInUser) -> str | HTML:
        raise CSVExportError()

    def export_for_json(self, row: Row, cell: Cell, user: LoggedInUser) -> dict:
        return render_tree_json(row, user=user, request=self.request)


def render_tree_json(
    row: typing.Mapping[str, typing.Any],
    *,
    user: LoggedInUser,
    request: Request,
) -> dict[str, Any]:
    expansion_level = request.get_integer_input_mandatory("expansion_level", 999)

    if expansion_level != user.bi_expansion_level:
        treestate: dict[str, Any] = {}
        user.set_tree_states("bi", treestate)
        if not isinstance(user, LoggedInSuperUser):
            user.save_tree_states()

    def render_node_json(
        tree: BIAggrTreeState | BILeafTreeState, show_host: bool
    ) -> dict[str, Any]:
        is_leaf = len(tree) == 3
        if is_leaf:
            service = tree[2].get("service")
            if not service:
                title = _("Host state")
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

    def render_subtree_json(
        node: BIAggrTreeState | BILeafTreeState, path: Sequence[str], show_host: bool
    ) -> dict[str, Any]:
        json_node = render_node_json(node, show_host)

        is_next_level_open = len(path) <= expansion_level

        if is_aggr(node) and is_next_level_open:
            json_node["nodes"] = []
            for child_node in node[3]:
                if not child_node[2].get("hidden"):
                    new_path = [*path, child_node[2]["title"]]
                    json_node["nodes"].append(render_subtree_json(child_node, new_path, show_host))

        return json_node

    root_node = row["aggr_treestate"]
    affected_hosts = row["aggr_hosts"]

    return render_subtree_json(root_node, [root_node[2]["title"]], len(affected_hosts) > 1)


def compute_output_message(effective_state: dict[str, Any], rule: dict[str, Any]) -> str:
    output = []
    if effective_state["output"]:
        output.append(effective_state["output"])

    str_state = str(effective_state["state"])
    if str_state in rule.get("state_messages", {}):
        output.append(escape_attribute(rule["state_messages"][str_state]))
    return ", ".join(output)


PermissionFreezeAggregation = permission_registry.register(
    Permission(
        section=PERMISSION_SECTION_ACTION,
        name="aggregation_freeze",
        title=_l("Freeze aggregations"),
        description=_l("Freeze aggregations"),
        defaults=["user", "admin"],
    )
)


class CommandGroupAggregations(CommandGroup):
    @property
    def ident(self) -> str:
        return "aggregations"

    @property
    def title(self) -> str:
        return _("Aggregations")

    @property
    def sort_index(self) -> int:
        return 10


def command_freeze_aggregation_render(what: str) -> None:
    html.open_div(class_="group")
    html.button(_button_name(), _("Freeze selected"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_freeze_aggregation_affected(
    len_action_rows: int, cmdtag: Literal["HOST", "SVC"]
) -> HTML:
    return HTML.without_escaping(
        _("Affected %s: %s")
        % (
            ungettext(
                "aggregation",
                "aggregations",
                len_action_rows,
            ),
            len_action_rows,
        )
    )


def _button_name() -> str:
    return "_freeze_aggregations"


def command_freeze_aggregation_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if not request.has_var(_button_name()):
        return None

    if (compiled_aggregation := row.get("aggr_compiled_aggregation")) is not None:
        if frozen_info := compiled_aggregation.frozen_info:
            frozen_path = storage.FrozenAggregationStore(
                get_default_site_filesystem().var
            ).get_branch_path(
                aggregation_id=frozen_info.based_on_aggregation_id,
                branch_title=compiled_aggregation.id,
            )
            return (
                Dummy(str(frozen_path)),
                command.confirm_dialog_options(cmdtag, row, action_rows),
            )

    return None


def command_freeze_aggregation_executor(command: CommandSpec, site: SiteId | None) -> None:
    """Function that is called to execute this action"""
    assert isinstance(command, Dummy)
    Path(command.arg).unlink(missing_ok=True)


CommandFreezeAggregation = Command(
    ident="freeze_aggregation",
    title=_l("Freeze aggregations"),
    confirm_title=_l("Freeze aggregation?"),
    confirm_button=_l("Freeze"),
    icon_name=DynamicIconName("bi_freeze"),
    is_shortcut=True,
    is_suggested=True,
    permission=PermissionFreezeAggregation,
    group=CommandGroupAggregations,
    tables=["aggr"],
    only_view="aggr_frozen_diff",
    render=command_freeze_aggregation_render,
    action=command_freeze_aggregation_action,
    affected_output_cb=command_freeze_aggregation_affected,
    executor=command_freeze_aggregation_executor,
)
