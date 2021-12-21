#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

import cmk.gui.sites as sites
from cmk.gui.globals import html, request
from cmk.gui.i18n import _
from cmk.gui.plugins.sidebar.utils import link, SidebarSnapin, snapin_registry
from cmk.gui.utils.urls import makeuri_contextless


class HostSnapin(SidebarSnapin, abc.ABC):
    @abc.abstractmethod
    def _host_mode_ident(self) -> str:
        raise NotImplementedError()

    def show(self) -> None:
        mode = self._host_mode_ident()
        sites.live().set_prepend_site(True)
        query = "GET hosts\nColumns: name state worst_service_state\nLimit: 100\n"
        view = "host"

        if mode == "problems":
            view = "problemsofhost"
            # Exclude hosts and services in downtime
            svc_query = (
                "GET services\nColumns: host_name\n"
                "Filter: state > 0\nFilter: scheduled_downtime_depth = 0\n"
                "Filter: host_scheduled_downtime_depth = 0\nAnd: 3"
            )
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
            link(
                text=host,
                url=makeuri_contextless(
                    request,
                    [
                        ("view_name", view),
                        ("host", host),
                        ("site", site),
                    ],
                    filename="view.py",
                ),
            )
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
    def refresh_on_restart(cls) -> bool:
        return True


@snapin_registry.register
class Hosts(HostSnapin):
    def _host_mode_ident(self) -> str:
        return "hosts"

    @staticmethod
    def type_name() -> str:
        return "hosts"

    @classmethod
    def title(cls) -> str:
        return _("All hosts")

    @classmethod
    def description(cls) -> str:
        return _("A summary state of each host with a link to the view showing its services")


@snapin_registry.register
class ProblemHosts(HostSnapin):
    def _host_mode_ident(self) -> str:
        return "problems"

    @staticmethod
    def type_name() -> str:
        return "problem_hosts"

    @classmethod
    def title(cls) -> str:
        return _("Problem hosts")

    @classmethod
    def description(cls) -> str:
        return _(
            "A summary state of all hosts that have a problem, with "
            "links to problems of those hosts"
        )

    @classmethod
    def refresh_regularly(cls) -> bool:
        return True
