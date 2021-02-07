#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.sites as sites
import cmk.gui.visuals as visuals
from cmk.gui.i18n import _
from cmk.gui.globals import html


# This base class is only used by HostMatrixVisualization so far
# TODO: Implement a ServiceMatrixVisualization class
class MatrixVisualization:
    @classmethod
    def livestatus_table(cls):
        return NotImplementedError

    @classmethod
    def livestatus_columns(cls):
        return NotImplementedError

    @classmethod
    def filter_infos(cls):
        return NotImplementedError

    def show(self, width, context):
        return NotImplementedError

    def _get_livestatus(self, context):
        context_filters, only_sites = visuals.get_filter_headers(table=self.livestatus_table(),
                                                                 infos=self.filter_infos(),
                                                                 context=context)
        return self._execute_query(self._get_query(context_filters), only_sites)

    def _execute_query(self, query, only_sites):
        try:
            sites.live().set_prepend_site(True)
            if only_sites:
                sites.live().set_only_sites(only_sites)
            return sites.live().query(query)
        finally:
            sites.live().set_only_sites(None)
            sites.live().set_prepend_site(False)

    def _get_query(self, context_filters):
        query = ("GET %s\n"
                 "Columns: %s\n"
                 "Limit: 901\n" %
                 (self.livestatus_table(), self.livestatus_columns())) + context_filters
        return query


class HostMatrixVisualization(MatrixVisualization):
    @classmethod
    def livestatus_table(cls):
        return "hosts"

    @classmethod
    def livestatus_columns(cls):
        return "name state has_been_checked worst_service_state scheduled_downtime_depth"

    @classmethod
    def filter_infos(cls):
        return ["host"]

    def show(self, width, context):
        hosts = self._get_livestatus(context)
        num_hosts = len(hosts)

        if num_hosts > 900:
            html.write_text(_("Sorry, I will not display more than 900 hosts."))
            return

        # Choose smallest square number large enough
        # to show all hosts
        n = 1
        while n * n < num_hosts:
            n += 1

        rows = int(num_hosts / n)
        lastcols = num_hosts % n
        if lastcols > 0:
            rows += 1

        # Calculate cell size (Automatic sizing with 100% does not work here)
        # - Get cell spacing: 1px between each cell
        # - Substract the cell spacing for each column from the total width
        # - Then divide the total width through the number of columns
        # - Then get the full-digit width of the cell and summarize the rest
        #   to be substracted from the cell width
        # This is not a 100% solution but way better than having no links
        cell_spacing = 4
        cell_size = int((width - cell_spacing * (n + 1)) / n)
        style = 'width:%spx' % width

        html.open_table(class_=["content_center", "hostmatrix"], style=[style])
        col = 1
        row = 1
        for site, host, state, has_been_checked, worstsvc, downtimedepth in sorted(hosts):
            if col == 1:
                html.open_tr()
            if downtimedepth > 0:
                s = "d"
            elif not has_been_checked:
                s = "p"
            elif worstsvc == 2 or state == 1:
                s = "2"
            elif worstsvc == 3 or state == 2:
                s = "3"
            elif worstsvc == 1:
                s = "1"
            else:
                s = "0"
            url = "view.py?view_name=host&site=%s&host=%s" % (html.urlencode(site),
                                                              html.urlencode(host))
            html.open_td(class_=["state", "state%s" % s])
            html.a('',
                   href=url,
                   title=host,
                   target="main",
                   style=["width:%spx;" % cell_size,
                          "height:%spx;" % (2 * cell_size / 3)])
            html.close_td()

            if col == n or (row == rows and n == lastcols):
                html.open_tr()
                col = 1
                row += 1
            else:
                col += 1
        html.close_table()
