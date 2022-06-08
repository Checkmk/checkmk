#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple, Type, TYPE_CHECKING, Union

from livestatus import OnlySites

from cmk.utils.defines import short_service_state_name

import cmk.gui.bi as bi
import cmk.gui.utils.escaping as escaping
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.plugins.views.utils import (
    ABCDataSource,
    Cell,
    CellSpec,
    data_source_registry,
    Painter,
    painter_option_registry,
    painter_registry,
    PainterOption,
    PainterOptions,
    Row,
    RowTable,
)
from cmk.gui.type_defs import ColumnName, Rows, SingleInfos
from cmk.gui.utils.html import HTML
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.utils.urls import makeuri, urlencode_vars
from cmk.gui.valuespec import DropdownChoice, ValueSpec

if TYPE_CHECKING:
    from cmk.gui.plugins.visuals.utils import Filter
    from cmk.gui.views import View


#     ____        _
#    |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___
#    | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#    | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#    |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#


@data_source_registry.register
class DataSourceBIAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_aggregations"

    @property
    def title(self) -> str:
        return _("BI Aggregations")

    @property
    def table(self) -> "RowTable":
        return RowTableBIAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "aggr_group"]

    @property
    def unsupported_columns(self) -> List[ColumnName]:
        return ["site"]

    @property
    def keys(self) -> List[ColumnName]:
        return []

    @property
    def id_keys(self) -> List[ColumnName]:
        return ["aggr_name"]


class RowTableBIAggregations(RowTable):
    def query(
        self,
        view: View,
        columns: List[ColumnName],
        headers: str,
        only_sites: OnlySites,
        limit: Optional[int],
        all_active_filters: List[Filter],
    ) -> Union[Rows, Tuple[Rows, int]]:
        return bi.table(view.context, columns, headers, only_sites, limit, all_active_filters)


@data_source_registry.register
class DataSourceBIHostAggregations(ABCDataSource):
    @property
    def ident(self) -> str:
        return "bi_host_aggregations"

    @property
    def title(self) -> str:
        return _("BI Aggregations affected by one host")

    @property
    def table(self) -> "RowTable":
        return RowTableBIHostAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self) -> List[ColumnName]:
        return []

    @property
    def id_keys(self) -> List[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.host_table(view, columns, headers, only_sites, limit, all_active_filters)


@data_source_registry.register
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
    def table(self) -> "RowTable":
        return RowTableBIHostnameAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self) -> List[ColumnName]:
        return []

    @property
    def id_keys(self) -> List[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostnameAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.hostname_table(view, columns, headers, only_sites, limit, all_active_filters)


@data_source_registry.register
class DataSourceBIHostnameByGroupAggregations(ABCDataSource):
    """The same but with group information"""

    @property
    def ident(self) -> str:
        return "bi_hostnamebygroup_aggregations"

    @property
    def title(self) -> str:
        return _("BI aggregations for hosts by host groups")

    @property
    def table(self) -> "RowTable":
        return RowTableBIHostnameByGroupAggregations()

    @property
    def infos(self) -> SingleInfos:
        return ["aggr", "host", "hostgroup", "aggr_group"]

    @property
    def keys(self) -> List[ColumnName]:
        return []

    @property
    def id_keys(self) -> List[ColumnName]:
        return ["aggr_name"]


class RowTableBIHostnameByGroupAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.hostname_by_group_table(
            view, columns, headers, only_sites, limit, all_active_filters
        )


#     ____       _       _
#    |  _ \ __ _(_)_ __ | |_ ___ _ __ ___
#    | |_) / _` | | '_ \| __/ _ \ '__/ __|
#    |  __/ (_| | | | | | ||  __/ |  \__ \
#    |_|   \__,_|_|_| |_|\__\___|_|  |___/
#


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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
        return "", escaping.escape_attribute(row["aggr_group"])


@painter_registry.register
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
        return "", escaping.escape_attribute(row["aggr_name"])


@painter_registry.register
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


@painter_registry.register
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


@painter_registry.register
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


@painter_option_registry.register
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


@painter_option_registry.register
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


@painter_option_registry.register
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


@painter_option_registry.register
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
    row: Row, force_renderer_cls: Optional[Type[bi.ABCFoldableTreeRenderer]] = None
) -> CellSpec:
    if html.is_api_call():
        return bi.render_tree_json(row)

    painter_options = PainterOptions.get_instance()
    treetype = painter_options.get("aggr_treetype")
    expansion_level = int(painter_options.get("aggr_expand"))
    only_problems = painter_options.get("aggr_onlyproblems") == "1"
    wrap_texts = painter_options.get("aggr_wrap")

    if force_renderer_cls:
        cls = force_renderer_cls
    elif treetype == "foldable":
        cls = bi.FoldableTreeRendererTree
    elif treetype in ["boxes", "boxes-omit-root"]:
        cls = bi.FoldableTreeRendererBoxes
    elif treetype == "bottom-up":
        cls = bi.FoldableTreeRendererBottomUp
    elif treetype == "top-down":
        cls = bi.FoldableTreeRendererTopDown
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


@painter_registry.register
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


@painter_registry.register
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
        return paint_aggregated_tree_state(row, force_renderer_cls=bi.FoldableTreeRendererBoxes)
