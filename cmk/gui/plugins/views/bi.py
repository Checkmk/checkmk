#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

from cmk.utils.defines import short_service_state_name

import cmk.gui.bi as bi
from cmk.gui.valuespec import (DropdownChoice)
from cmk.gui.htmllib import HTML
from cmk.gui.i18n import _
from cmk.gui.globals import html

from cmk.gui.plugins.views import (
    data_source_registry,
    DataSource,
    RowTable,
    PainterOptions,
    painter_option_registry,
    PainterOption,
    painter_registry,
    Painter,
)

#     ____        _
#    |  _ \  __ _| |_ __ _ ___  ___  _   _ _ __ ___ ___  ___
#    | | | |/ _` | __/ _` / __|/ _ \| | | | '__/ __/ _ \/ __|
#    | |_| | (_| | || (_| \__ \ (_) | |_| | | | (_|  __/\__ \
#    |____/ \__,_|\__\__,_|___/\___/ \__,_|_|  \___\___||___/
#


@data_source_registry.register
class DataSourceBIAggregations(DataSource):
    @property
    def ident(self):
        return "bi_aggregations"

    @property
    def title(self):
        return _("BI Aggregations")

    @property
    def table(self):
        return RowTableBIAggregations()

    @property
    def infos(self):
        return ["aggr", "aggr_group"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["aggr_name"]


class RowTableBIAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.table(view, columns, headers, only_sites, limit, all_active_filters)


@data_source_registry.register
class DataSourceBIHostAggregations(DataSource):
    @property
    def ident(self):
        return "bi_host_aggregations"

    @property
    def title(self):
        return _("BI Aggregations affected by one host")

    @property
    def table(self):
        return RowTableBIHostAggregations()

    @property
    def infos(self):
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["aggr_name"]


class RowTableBIHostAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.host_table(view, columns, headers, only_sites, limit, all_active_filters)


@data_source_registry.register
class DataSourceBIHostnameAggregations(DataSource):
    """Similar to host aggregations, but the name of the aggregation
    is used to join the host table rather then the affected host"""

    @property
    def ident(self):
        return "bi_hostname_aggregations"

    @property
    def title(self):
        return _("BI Hostname Aggregations")

    @property
    def table(self):
        return RowTableBIHostnameAggregations()

    @property
    def infos(self):
        return ["aggr", "host", "aggr_group"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["aggr_name"]


class RowTableBIHostnameAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.hostname_table(view, columns, headers, only_sites, limit, all_active_filters)


@data_source_registry.register
class DataSourceBIHostnameByGroupAggregations(DataSource):
    """The same but with group information"""

    @property
    def ident(self):
        return "bi_hostnamebygroup_aggregations"

    @property
    def title(self):
        return _("BI Aggregations for Hosts by Hostgroups")

    @property
    def table(self):
        return RowTableBIHostnameByGroupAggregations()

    @property
    def infos(self):
        return ["aggr", "host", "hostgroup", "aggr_group"]

    @property
    def keys(self):
        return []

    @property
    def id_keys(self):
        return ["aggr_name"]


class RowTableBIHostnameByGroupAggregations(RowTable):
    def query(self, view, columns, headers, only_sites, limit, all_active_filters):
        return bi.hostname_by_group_table(view, columns, headers, only_sites, limit,
                                          all_active_filters)


#     ____       _       _
#    |  _ \ __ _(_)_ __ | |_ ___ _ __ ___
#    | |_) / _` | | '_ \| __/ _ \ '__/ __|
#    |  __/ (_| | | | | | ||  __/ |  \__ \
#    |_|   \__,_|_|_| |_|\__\___|_|  |___/
#


@painter_registry.register
class PainterAggrIcons(Painter):
    @property
    def ident(self):
        return "aggr_icons"

    @property
    def title(self):
        return _("Links")

    @property
    def columns(self):
        return ['aggr_group', 'aggr_name', 'aggr_effective_state']

    @property
    def printable(self):
        return False

    def render(self, row, cell):
        single_url = "view.py?" + html.urlencode_vars([("view_name", "aggr_single"),
                                                       ("aggr_name", row["aggr_name"])])
        avail_url = single_url + "&mode=availability"

        bi_map_url = "bi_map.py?" + html.urlencode_vars([
            ("aggr_name", row["aggr_name"]),
        ])

        with html.plugged():
            html.icon_button(bi_map_url, _("Visualize this aggregation"), "aggr")
            html.icon_button(single_url, _("Show only this aggregation"), "showbi")
            html.icon_button(avail_url, _("Analyse availability of this aggregation"),
                             "availability")
            if row["aggr_effective_state"]["in_downtime"] != 0:
                html.icon(
                    _("A service or host in this aggregation is in downtime."), "derived_downtime")
            if row["aggr_effective_state"]["acknowledged"]:
                html.icon(
                    _("The critical problems that make this aggregation non-OK have been acknowledged."
                     ), "ack")
            if not row["aggr_effective_state"]["in_service_period"]:
                html.icon(
                    _("This aggregation is currently out of its service period."),
                    "outof_serviceperiod")
            code = html.drain()
        return "buttons", code


@painter_registry.register
class PainterAggrInDowntime(Painter):
    @property
    def ident(self):
        return "aggr_in_downtime"

    @property
    def title(self):
        return _("In Downtime")

    @property
    def columns(self):
        return ['aggr_effective_state']

    def render(self, row, cell):
        return ("", (row["aggr_effective_state"]["in_downtime"] and "1" or "0"))


@painter_registry.register
class PainterAggrAcknowledged(Painter):
    @property
    def ident(self):
        return "aggr_acknowledged"

    @property
    def title(self):
        return _("Acknowledged")

    @property
    def columns(self):
        return ['aggr_effective_state']

    def render(self, row, cell):
        return ("", (row["aggr_effective_state"]["acknowledged"] and "1" or "0"))


def paint_aggr_state_short(state, assumed=False):
    if state is None:
        return "", ""
    else:
        name = short_service_state_name(state["state"], "")
        classes = "state svcstate state%s" % state["state"]
        if assumed:
            classes += " assumed"
        return classes, name


@painter_registry.register
class PainterAggrState(Painter):
    @property
    def ident(self):
        return "aggr_state"

    @property
    def title(self):
        return _("Aggregated state")

    @property
    def short_title(self):
        return _("State")

    @property
    def columns(self):
        return ['aggr_effective_state']

    def render(self, row, cell):
        return paint_aggr_state_short(row["aggr_effective_state"],
                                      row["aggr_effective_state"] != row["aggr_state"])


@painter_registry.register
class PainterAggrStateNum(Painter):
    @property
    def ident(self):
        return "aggr_state_num"

    @property
    def title(self):
        return _("Aggregated state (number)")

    @property
    def short_title(self):
        return _("State")

    @property
    def columns(self):
        return ['aggr_effective_state']

    def render(self, row, cell):
        return ("", str(row["aggr_effective_state"]['state']))


@painter_registry.register
class PainterAggrRealState(Painter):
    @property
    def ident(self):
        return "aggr_real_state"

    @property
    def title(self):
        return _("Aggregated real state (never assumed)")

    @property
    def short_title(self):
        return _("R.State")

    @property
    def columns(self):
        return ['aggr_state']

    def render(self, row, cell):
        return paint_aggr_state_short(row["aggr_state"])


@painter_registry.register
class PainterAggrAssumedState(Painter):
    @property
    def ident(self):
        return "aggr_assumed_state"

    @property
    def title(self):
        return _("Aggregated assumed state")

    @property
    def short_title(self):
        return _("Assumed")

    @property
    def columns(self):
        return ['aggr_assumed_state']

    def render(self, row, cell):
        return paint_aggr_state_short(row["aggr_assumed_state"])


@painter_registry.register
class PainterAggrGroup(Painter):
    @property
    def ident(self):
        return "aggr_group"

    @property
    def title(self):
        return _("Aggregation group")

    @property
    def short_title(self):
        return _("Group")

    @property
    def columns(self):
        return ['aggr_group']

    def render(self, row, cell):
        return ("", html.attrencode(row["aggr_group"]))


@painter_registry.register
class PainterAggrName(Painter):
    @property
    def ident(self):
        return "aggr_name"

    @property
    def title(self):
        return _("Aggregation name")

    @property
    def short_title(self):
        return _("Aggregation")

    @property
    def columns(self):
        return ['aggr_name']

    def render(self, row, cell):
        return ("", html.attrencode(row["aggr_name"]))


@painter_registry.register
class PainterAggrOutput(Painter):
    @property
    def ident(self):
        return "aggr_output"

    @property
    def title(self):
        return _("Aggregation status output")

    @property
    def short_title(self):
        return _("Output")

    @property
    def columns(self):
        return ['aggr_output']

    def render(self, row, cell):
        return ("", row["aggr_output"])


def paint_aggr_hosts(row, link_to_view):
    h = []
    for site, host in row["aggr_hosts"]:
        url = html.makeuri([("view_name", link_to_view), ("site", site), ("host", host)])
        h.append(html.render_a(host, url))
    return "", HTML(" ").join(h)


@painter_registry.register
class PainterAggrHosts(Painter):
    @property
    def ident(self):
        return "aggr_hosts"

    @property
    def title(self):
        return _("Aggregation: affected hosts")

    @property
    def short_title(self):
        return _("Hosts")

    @property
    def columns(self):
        return ['aggr_hosts']

    def render(self, row, cell):
        return paint_aggr_hosts(row, "aggr_host")


@painter_registry.register
class PainterAggrHostsServices(Painter):
    @property
    def ident(self):
        return "aggr_hosts_services"

    @property
    def title(self):
        return _("Aggregation: affected hosts (link to host page)")

    @property
    def short_title(self):
        return _("Hosts")

    @property
    def columns(self):
        return ['aggr_hosts']

    def render(self, row, cell):
        return paint_aggr_hosts(row, "host")


@painter_option_registry.register
class PainterOptionAggrExpand(PainterOption):
    @property
    def ident(self):
        return "aggr_expand"

    @property
    def valuespec(self):
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
    def ident(self):
        return "aggr_onlyproblems"

    @property
    def valuespec(self):
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
    def ident(self):
        return "aggr_treetype"

    @property
    def valuespec(self):
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
    def ident(self):
        return "aggr_wrap"

    @property
    def valuespec(self):
        return DropdownChoice(
            title=_("Handling of too long texts (affects only table)"),
            default_value="wrap",
            choices=[
                ("wrap", _("wrap")),
                ("nowrap", _("don't wrap")),
            ],
        )


def paint_aggregated_tree_state(row, force_renderer_cls=None):
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
        wrap_texts=wrap_texts)
    return renderer.css_class(), renderer.render()


@painter_registry.register
class PainterAggrTreestate(Painter):
    @property
    def ident(self):
        return "aggr_treestate"

    @property
    def title(self):
        return _("Aggregation: complete tree")

    @property
    def short_title(self):
        return _("Tree")

    @property
    def columns(self):
        return ['aggr_treestate', 'aggr_hosts']

    @property
    def painter_options(self):
        return ['aggr_expand', 'aggr_onlyproblems', 'aggr_treetype', 'aggr_wrap']

    def render(self, row, cell):
        return paint_aggregated_tree_state(row)


@painter_registry.register
class PainterAggrTreestateBoxed(Painter):
    @property
    def ident(self):
        return "aggr_treestate_boxed"

    @property
    def title(self):
        return _("Aggregation: simplistic boxed layout")

    @property
    def short_title(self):
        return _("Tree")

    @property
    def columns(self):
        return ['aggr_treestate', 'aggr_hosts']

    def render(self, row, cell):
        return paint_aggregated_tree_state(row, force_renderer_cls=bi.FoldableTreeRendererBoxes)
