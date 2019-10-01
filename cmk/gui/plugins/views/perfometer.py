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

import cmk.gui.config as config
import cmk.gui.metrics as metrics
from cmk.gui.i18n import _

from cmk.gui.globals import html
from cmk.gui.htmllib import HTML

from cmk.gui.log import logger

from cmk.gui.plugins.views.perfometers import (
    perfometers,
    render_metricometer,
)

from cmk.gui.plugins.views import (
    painter_registry,
    Painter,
    sorter_registry,
    Sorter,
    is_stale,
    display_options,
    pnp_url,
)


class Perfometer(object):
    def __init__(self, row):
        super(Perfometer, self).__init__()

        self._row = row

        self._perf_data = []
        self._check_command = self._row["service_check_command"]
        self._translated_metrics = None

        self._parse_perf_data()

    def _parse_perf_data(self):
        perf_data_string = self._row["service_perf_data"].decode("utf-8").strip()
        if not perf_data_string:
            return

        self._perf_data, self._check_command = metrics.parse_perf_data(
            perf_data_string, self._row["service_check_command"])

        self._translated_metrics = metrics.translate_metrics(self._perf_data, self._check_command)

    def render(self):
        """Renders the HTML code of a perfometer

        It returns a 2-tuple of either the title to show and the HTML of
        the perfometer or both elements set to None in case nothing shal
        be shown.
        """
        if not self._perf_data:
            return None, None

        # Try new metrics module
        title, h = self._render_metrics_perfometer()
        if title is not None:
            return title, h

        if not self._has_legacy_perfometer():
            return None, None

        # Legacy Perf-O-Meters: find matching Perf-O-Meter function
        logger.info("Legacy perfometer rendered for %s / %s / %s", self._row["host_name"],
                    self._row["service_description"], self._row["service_check_command"])
        return self._render_legacy_perfometer()

    def _render_metrics_perfometer(self):
        perfometer_definition = self._get_perfometer_definition(self._translated_metrics)
        if not perfometer_definition:
            return None, None

        renderer = metrics.renderer_registry.get_renderer(perfometer_definition,
                                                          self._translated_metrics)
        return renderer.get_label(), render_metricometer(renderer.get_stack())

    def _render_legacy_perfometer(self):
        perf_painter = perfometers[self._check_command]
        title, h = perf_painter(self._row, self._check_command, self._perf_data)
        if not h:
            return None, None

        return title, h

    def sort_value(self):
        """Calculates a value that is used for sorting perfometers

        - First sort by the perfometer group / id
        - Second by the sort value calculated based on the perfometer type and
          the actual data
        """
        return self._get_sort_group(), self._get_sort_number()

    def _get_sort_group(self):
        """First sort by the optional performeter group or the perfometer id. The perfometer
          group is used to group different perfometers in a single sort domain
        """
        sort_group = self._get_metrics_sort_group()

        if sort_group:
            return sort_group

        # TODO: Remove this legacy handling one day
        if not self._has_legacy_perfometer():
            return None

        # Fallback to legacy perfometer sorting. sort by the id() of the render function.
        # This should automatically group similar perfometers together.
        perf_painter_func = perfometers[self._check_command]
        return id(perf_painter_func)

    def _get_metrics_sort_group(self):
        perfometer_definition = self._get_perfometer_definition(self._translated_metrics)
        if not perfometer_definition:
            return None

        # The perfometer definitions had no ID until implementation of this sorting. We need to
        # care about this here. Since it is only for grouping perfometers of the same type, we
        # can use the id() of the perfometer_definition here.
        return perfometer_definition.get("sort_group", id(perfometer_definition))

    def _get_sort_number(self):
        """Calculate the sort value for this perfometer
        - The second sort criteria is a number that is calculated for each perfometer. The
          calculation of this number depends on the perfometer type:
          - Dual: sort by max(left, right). e.g. for traffic graphs it seems to be useful to
            make it sort by the maximum traffic independent of the direction.
          - Stacked: Use the number of the first stack element.
          - TODO: Make it possible to define a custom "sort_by" formula like it's done in other
            places of the metric system. Something like this: "sort_by": "user,system,+,idle,+,nice,+"
        """
        sort_number = self._get_metrics_sort_number()

        if sort_number is not None:
            return sort_number

        # TODO: Remove this legacy handling one day
        if not self._has_legacy_perfometer():
            return None

        # TODO: Fallback to legacy perfometer number calculation
        return None

    def _get_metrics_sort_number(self):
        perfometer_definition = self._get_perfometer_definition(self._translated_metrics)
        if not perfometer_definition:
            return None

        renderer = metrics.renderer_registry.get_renderer(perfometer_definition,
                                                          self._translated_metrics)
        return renderer.get_sort_number()

    def _get_perfometer_definition(self, translated_metrics):
        """Returns the matching perfometer definition

        Uses the metrics of the current row to gather perfometers that can be
        rendered using these metrics. The first found perfometer definition
        is used.

        Returns None in case there is no matching definition found.
        """
        perfometer_definitions = metrics.Perfometers().get_matching_perfometers(translated_metrics)
        if not perfometer_definitions:
            return

        return perfometer_definitions[0]

    def _has_legacy_perfometer(self):
        return self._check_command in perfometers


#.
#   .--Painter-------------------------------------------------------------.
#   |                   ____       _       _                               |
#   |                  |  _ \ __ _(_)_ __ | |_ ___ _ __                    |
#   |                  | |_) / _` | | '_ \| __/ _ \ '__|                   |
#   |                  |  __/ (_| | | | | | ||  __/ |                      |
#   |                  |_|   \__,_|_|_| |_|\__\___|_|                      |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | The perfometers are registered through a painter and sorter          |
#   '----------------------------------------------------------------------'


@painter_registry.register
class PainterPerfometer(Painter):
    @property
    def ident(self):
        return "perfometer"

    @property
    def title(self):
        return _("Service Perf-O-Meter")

    @property
    def short_title(self):
        return _("Perf-O-Meter")

    @property
    def columns(self):
        return [
            'service_staleness',
            'service_perf_data',
            'service_state',
            'service_check_command',
            'service_pnpgraph_present',
            'service_plugin_output',
        ]

    @property
    def printable(self):
        return 'perfometer'

    def render(self, row, cell):
        classes = ["perfometer"]
        if is_stale(row):
            classes.append("stale")

        try:
            title, h = Perfometer(row).render()
            if title is None and h is None:
                return "", ""
        except Exception as e:
            logger.exception("error rendering performeter")
            if config.debug:
                raise
            return " ".join(classes), _("Exception: %s") % e

        content = html.render_div(HTML(h), class_=["content"]) \
                + html.render_div(title, class_=["title"]) \
                + html.render_div("", class_=["glass"])

        # pnpgraph_present: -1 means unknown (path not configured), 0: no, 1: yes
        if display_options.enabled(display_options.X) \
           and row["service_pnpgraph_present"] != 0:
            if metrics.cmk_graphs_possible():
                import cmk.gui.cee.plugins.views.graphs
                url = cmk.gui.cee.plugins.views.graphs.cmk_graph_url(row, "service")
            else:
                url = pnp_url(row, "service")
            disabled = False
        else:
            url = "javascript:void(0)"
            disabled = True

        return " ".join(classes), \
            html.render_a(content=content, href=url, title=html.strip_tags(title),
                          class_=["disabled" if disabled else None])


@sorter_registry.register
class SorterPerfometer(Sorter):
    @property
    def ident(self):
        return "perfometer"

    @property
    def title(self):
        return _("Perf-O-Meter")

    @property
    def columns(self):
        return [
            'service_perf_data', 'service_state', 'service_check_command',
            'service_pnpgraph_present', 'service_plugin_output'
        ]

    def cmp(self, r1, r2):
        try:
            p1 = Perfometer(r1)
            p2 = Perfometer(r2)
            return (p1.sort_value() > p2.sort_value()) - (p1.sort_value() < p2.sort_value())
        except Exception:
            logger.exception("error sorting perfometer values")
            if config.debug:
                raise
            return 0
