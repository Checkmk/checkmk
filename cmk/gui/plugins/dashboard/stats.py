#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import Tuple, List  # pylint: disable=unused-import
import six

from livestatus import MKLivestatusNotFoundError
import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from cmk.gui.plugins.dashboard import (
    Dashlet,
    dashlet_registry,
)


class DashletStats(six.with_metaclass(abc.ABCMeta, Dashlet)):
    @classmethod
    def is_resizable(cls):
        return False

    @classmethod
    def initial_size(cls):
        return (30, 18)

    @classmethod
    def initial_refresh_interval(cls):
        return 60

    @classmethod
    def has_context(cls):
        return True

    @abc.abstractmethod
    def _livestatus_table(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _table(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _filter(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def _view_name(self):
        raise NotImplementedError()

    # TODO: Refactor this method
    def show(self):
        pie_id = "dashlet_%d" % self._dashlet_id
        pie_diameter = 130
        pie_left_aspect = 0.5
        pie_right_aspect = 0.8
        table = self._table()

        filter_headers, only_sites = visuals.get_filter_headers(table=self._livestatus_table(),
                                                                infos=self.infos(),
                                                                context=self.context)

        query = "GET %s\n" % self._livestatus_table()
        for entry in table:
            query += entry[3]
        query += self._filter() + filter_headers

        if only_sites:
            try:
                sites.live().set_only_sites(only_sites)
                result = sites.live().query_row(query)  # type: List[int]
            finally:
                sites.live().set_only_sites()
        else:
            try:
                result = sites.live().query_summed_stats(query)
            except MKLivestatusNotFoundError:
                result = []

        pies = list(zip(table, result))
        total = sum([x[1] for x in pies])

        html.open_div(class_="stats")
        html.canvas('',
                    class_="pie",
                    id_="%s_stats" % pie_id,
                    width="%d" % pie_diameter,
                    height="%d" % pie_diameter,
                    style="float: left")
        html.img(html.theme_url("images/globe.png"), class_="globe")

        html.open_table(class_=["hoststats"] + (["narrow"] if len(pies) > 0 else []),
                        style="float:left")

        table_entries = []  # type: List[Tuple]
        table_entries += pies
        while len(table_entries) < 6:
            table_entries = table_entries + [(("", None, [], ""), HTML("&nbsp;"))]
        table_entries.append(((_("Total"), "", [], ""), total))

        for (name, color, table_url_vars, query), count in table_entries:
            url_vars = [
                ("view_name", self._view_name()),
                ("filled_in", "filter"),
                ("search", "1"),
            ] + table_url_vars + self._dashlet_context_vars()
            url = html.makeuri_contextless(url_vars, filename="view.py")

            html.open_tr()
            html.th(html.render_a(name, href=url))
            html.td('', class_="color", style="background-color: %s" % color if color else '')
            html.td(html.render_a(count, href=url))
            html.close_tr()

        html.close_table()

        pie_parts = []
        if total > 0:
            # Count number of non-empty classes
            num_nonzero = 0
            for _info, value in pies:
                if value > 0:
                    num_nonzero += 1

            # Each non-zero class gets at least a view pixels of visible thickness.
            # We reserve that space right now. All computations are done in percent
            # of the radius.
            separator = 0.02  # 3% of radius
            remaining_separatorspace = num_nonzero * separator  # space for separators
            remaining_radius = 1 - remaining_separatorspace  # remaining space
            remaining_part = 1.0  # keep track of remaining part, 1.0 = 100%

            # Loop over classes, begin with most outer sphere. Inner spheres show
            # worse states and appear larger to the user (which is the reason we
            # are doing all this stuff in the first place)
            for (name, color, _unused, _q), value in pies[::1]:
                if value > 0 and remaining_part > 0:  # skip empty classes

                    # compute radius of this sphere *including all inner spheres!* The first
                    # sphere always gets a radius of 1.0, of course.
                    radius = remaining_separatorspace + remaining_radius * (remaining_part**
                                                                            (1 / 3.0))
                    pie_parts.append('chart_pie("%s", %f, %f, %r, true);' %
                                     (pie_id, pie_right_aspect, radius, color))
                    pie_parts.append('chart_pie("%s", %f, %f, %r, false);' %
                                     (pie_id, pie_left_aspect, radius, color))

                    # compute relative part of this class
                    part = float(value) / total  # ranges from 0 to 1
                    remaining_part -= part
                    remaining_separatorspace -= separator

        html.close_div()

        html.javascript(
            """
function chart_pie(pie_id, x_scale, radius, color, right_side) {
    var context = document.getElementById(pie_id + "_stats").getContext('2d');
    if (!context)
        return;
    var pie_x = %(x)f;
    var pie_y = %(y)f;
    var pie_d = %(d)f;
    context.fillStyle = color;
    context.save();
    context.translate(pie_x, pie_y);
    context.scale(x_scale, 1);
    context.beginPath();
    if(right_side)
        context.arc(0, 0, (pie_d / 2) * radius, 1.5 * Math.PI, 0.5 * Math.PI, false);
    else
        context.arc(0, 0, (pie_d / 2) * radius, 0.5 * Math.PI, 1.5 * Math.PI, false);
    context.closePath();
    context.fill();
    context.restore();
    context = null;
}


if (cmk.dashboard.has_canvas_support()) {
    %(p)s
}
""" % {
                "x": int(pie_diameter / 2.0),
                "y": int(pie_diameter / 2.0),
                "d": pie_diameter,
                'p': '\n'.join(pie_parts)
            })


@dashlet_registry.register
class HostStatsDashlet(DashletStats):
    """Dashlet that displays statistics about host states as globe and a table"""
    @classmethod
    def type_name(cls):
        return "hoststats"

    @classmethod
    def title(cls):
        return _("Host Statistics")

    @classmethod
    def description(cls):
        return _("Displays statistics about host states as globe and a table.")

    @classmethod
    def sort_index(cls):
        return 45

    @classmethod
    def infos(cls):
        # type: () -> List[str]
        return ["host"]

    def _livestatus_table(self):
        return "hosts"

    def _view_name(self):
        return "searchhost"

    # TODO: Refactor this data structure
    def _table(self):
        return [
            (
                _("Up"),
                "#0b3",
                [("is_host_scheduled_downtime_depth", "0"), ("hst0", "on")],
                "Stats: state = 0\n"  #
                "Stats: scheduled_downtime_depth = 0\n"  #
                "StatsAnd: 2\n"),
            (
                _("Down"),
                "#f00",
                [("is_host_scheduled_downtime_depth", "0"), ("hst1", "on")],
                "Stats: state = 1\n"  #
                "Stats: scheduled_downtime_depth = 0\n"  #
                "StatsAnd: 2\n"),
            (
                _("Unreachable"),
                "#f80",
                [("is_host_scheduled_downtime_depth", "0"), ("hst2", "on")],
                "Stats: state = 2\n"  #
                "Stats: scheduled_downtime_depth = 0\n"  #
                "StatsAnd: 2\n"),
            (_("In Downtime"), "#0af", [
                ("searchhost&search", "1"),
                ("is_host_scheduled_downtime_depth", "1"),
            ], "Stats: scheduled_downtime_depth > 0\n")
        ]

    def _filter(self):
        return "Filter: custom_variable_names < _REALNAME\n"


@dashlet_registry.register
class ServiceStatsDashlet(DashletStats):
    """Dashlet that displays statistics about service states as globe and a table"""
    @classmethod
    def type_name(cls):
        return "servicestats"

    @classmethod
    def title(cls):
        return _("Service Statistics")

    @classmethod
    def description(cls):
        return _("Displays statistics about service states as globe and a table.")

    @classmethod
    def sort_index(cls):
        return 50

    @classmethod
    def infos(cls):
        # type: () -> List[str]
        return ['host', 'service']

    def _livestatus_table(self):
        return "services"

    def _view_name(self):
        return "searchsvc"

    def _table(self):
        return [
            (_("OK"), "#0b3", [("hst0", "on"), ("st0", "on"),
                               ("is_in_downtime", "0")], "Stats: state = 0\n"
             "Stats: scheduled_downtime_depth = 0\n"
             "Stats: host_scheduled_downtime_depth = 0\n"
             "Stats: host_state = 0\n"
             "Stats: host_has_been_checked = 1\n"
             "StatsAnd: 5\n"),
            (_("In Downtime"), "#0af", [("is_in_downtime", "1")],
             "Stats: scheduled_downtime_depth > 0\n"
             "Stats: host_scheduled_downtime_depth > 0\n"
             "StatsOr: 2\n"),
            (_("On Down host"), "#048", [("hst1", "on"), ("hst2", "on"), ("hstp", "on"),
                                         ("is_in_downtime", "0")],
             "Stats: scheduled_downtime_depth = 0\n"
             "Stats: host_scheduled_downtime_depth = 0\n"
             "Stats: host_state != 0\n"
             "StatsAnd: 3\n"),
            (_("Warning"), "#ff0", [("hst0", "on"), ("st1", "on"),
                                    ("is_in_downtime", "0")], "Stats: state = 1\n"
             "Stats: scheduled_downtime_depth = 0\n"
             "Stats: host_scheduled_downtime_depth = 0\n"
             "Stats: host_state = 0\n"
             "Stats: host_has_been_checked = 1\n"
             "StatsAnd: 5\n"),
            (_("Unknown"), "#f80", [("hst0", "on"), ("st3", "on"),
                                    ("is_in_downtime", "0")], "Stats: state = 3\n"
             "Stats: scheduled_downtime_depth = 0\n"
             "Stats: host_scheduled_downtime_depth = 0\n"
             "Stats: host_state = 0\n"
             "Stats: host_has_been_checked = 1\n"
             "StatsAnd: 5\n"),
            (_("Critical"), "#f00", [("hst0", "on"), ("st2", "on"),
                                     ("is_in_downtime", "0")], "Stats: state = 2\n"
             "Stats: scheduled_downtime_depth = 0\n"
             "Stats: host_scheduled_downtime_depth = 0\n"
             "Stats: host_state = 0\n"
             "Stats: host_has_been_checked = 1\n"
             "StatsAnd: 5\n"),
        ]

    def _filter(self):
        return "Filter: host_custom_variable_names < _REALNAME\n"
