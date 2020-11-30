#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from requests import RequestException

from cmk.gui.cee.ntop.connector import NtopConnector as Connector
from cmk.gui.cee.ntop.globals import NtopException
from cmk.gui.i18n import _
from cmk.gui.plugins.visuals import filter_registry, FilterTristate


@filter_registry.register_instance
class FilterNtopInterface(FilterTristate):
    def __init__(self):
        super().__init__(
            ident="ntop_interface",
            title=_("Interface known in Ntop"),
            sort_index=300,
            info="host",
            column=None,
            is_show_more=True,
        )

    def filter(self, infoname):
        return ""

    def filter_table(self, rows):
        current = self.tristate_value()
        if current == -1:
            return rows
        new_rows = []
        try:
            connector = Connector()
            active_hosts = set(connector.fetch_active_hosts(connector.get_interface_ifid()))
        except (NtopException, RequestException):
            return rows

        for row in rows:
            is_part = row["host_name"] in active_hosts
            if (is_part and current == 1) or (not is_part and current == 0):
                new_rows.append(row)
        return new_rows

    def filter_code(self, infoname, positive):
        pass
