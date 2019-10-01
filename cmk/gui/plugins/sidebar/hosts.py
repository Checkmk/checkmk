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

import abc
import six

import cmk.gui.config as config
import cmk.gui.views as views
import cmk.gui.sites as sites
from cmk.gui.i18n import _
from cmk.gui.globals import html
from cmk.gui.plugins.sidebar import (
    link,
    SidebarSnapin,
    snapin_registry,
)


class HostSnapin(six.with_metaclass(abc.ABCMeta, SidebarSnapin)):
    @abc.abstractmethod
    def _host_mode_ident(self):
        raise NotImplementedError()

    def show(self):
        mode = self._host_mode_ident()
        sites.live().set_prepend_site(True)
        query = "GET hosts\nColumns: name state worst_service_state\nLimit: 100\n"
        view = "host"

        if mode == "problems":
            view = "problemsofhost"
            # Exclude hosts and services in downtime
            svc_query = "GET services\nColumns: host_name\n"\
                        "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\n"\
                        "Filter: host_scheduled_downtime_depth = 0\nAnd: 3"
            problem_hosts = {x[1] for x in sites.live().query(svc_query)}

            query += "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\nAnd: 2\n"
            for host in problem_hosts:
                query += "Filter: name = %s\n" % host
            query += "Or: %d\n" % (len(problem_hosts) + 1)

        hosts = sites.live().query(query)
        sites.live().set_prepend_site(False)
        hosts.sort()

        longestname = 0
        for site, host, state, worstsvc in hosts:
            longestname = max(longestname, len(host))
        if longestname > 15:
            num_columns = 1
        else:
            num_columns = 2

        target = views.get_context_link(config.user.id, view)
        html.open_table(class_="allhosts")
        col = 1
        for site, host, state, worstsvc in hosts:
            if col == 1:
                html.open_tr()
            html.open_td()

            if state > 0 or worstsvc == 2:
                statecolor = 2
            elif worstsvc == 1:
                statecolor = 1
            elif worstsvc == 3:
                statecolor = 3
            else:
                statecolor = 0
            html.open_div(class_=["statebullet", "state%d" % statecolor])
            html.nbsp()
            html.close_div()
            link(host, target + "&host=%s&site=%s" % (html.urlencode(host), html.urlencode(site)))
            html.close_td()
            if col == num_columns:
                html.close_tr()
                col = 1
            else:
                col += 1

        if col < num_columns:
            html.close_tr()
        html.close_table()

    @classmethod
    def refresh_on_restart(cls):
        return True


@snapin_registry.register
class Hosts(HostSnapin):
    def _host_mode_ident(self):
        return "hosts"

    @staticmethod
    def type_name():
        return "hosts"

    @classmethod
    def title(cls):
        return _("All Hosts")

    @classmethod
    def description(cls):
        return _("A summary state of each host with a link to the view showing its services")


@snapin_registry.register
class ProblemHosts(HostSnapin):
    def _host_mode_ident(self):
        return "problems"

    @staticmethod
    def type_name():
        return "problem_hosts"

    @classmethod
    def title(cls):
        return _("Problem Hosts")

    @classmethod
    def description(cls):
        return _("A summary state of all hosts that have a problem, with "
                 "links to problems of those hosts")
