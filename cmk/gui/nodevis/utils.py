#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Any

from livestatus import lqencode

from cmk.ccc import store
from cmk.ccc.hostaddress import HostName

import cmk.utils.paths
from cmk.utils.servicename import ServiceName

from cmk.gui import sites
from cmk.gui.config import active_config
from cmk.gui.i18n import _
from cmk.gui.page_menu import make_javascript_link, PageMenuEntry
from cmk.gui.watolib.utils import multisite_dir

topology_dir = cmk.utils.paths.var_dir / "topology"
topology_data_dir = topology_dir / "data"
topology_settings_lookup = topology_dir / "topology_settings"
topology_configs_dir = topology_dir / "configs"


@dataclass
class CMCHostObject:
    site: str
    hostname: HostName
    state: int
    alias: str
    icon_image: str | None
    address: str | None
    has_been_checked: int
    num_services_warn: int
    num_services_crit: int


@dataclass
class CMCServiceObject:
    site: str
    hostname: HostName
    name: str
    state: int
    icon_image: str | None


class BILayoutManagement:
    _config_file = multisite_dir() / "bi_layouts.mk"

    @classmethod
    def save_layouts(cls) -> None:
        store.save_to_mk_file(
            BILayoutManagement._config_file,
            key="bi_layouts",
            value=active_config.bi_layouts,
            pprint_value=True,
        )

    @classmethod
    def load_bi_aggregation_layout(cls, aggregation_name: str | None) -> Any:
        return active_config.bi_layouts["aggregations"].get(aggregation_name)

    @classmethod
    def get_all_bi_aggregation_layouts(cls) -> Any:
        return active_config.bi_layouts["aggregations"]


def get_toggle_layout_designer_page_menu_entry():
    return PageMenuEntry(
        title=_("Layout configuration"),
        icon_name="toggle_off",
        item=make_javascript_link(
            "const new_state = node_instance.toggle_layout_designer();"
            "cmk.d3.select('.suggestion.topology_layout_designer').select('img').classed('on', new_state);"
            "cmk.d3.select('#menu_shortcut_edit_layout').select('img').classed('on', new_state);"
        ),
        name="edit_layout",
        css_classes=["topology_layout_designer", "noselect"],
        is_shortcut=True,
        is_enabled=True,
    )


def get_compare_history_page_menu_entry():
    return PageMenuEntry(
        title=_("Compare history"),
        icon_name="toggle_off",
        item=make_javascript_link(
            "const new_state = node_instance.toggle_compare_history();"
            "cmk.d3.select('.suggestion.topology_compare_history').select('img').classed('on', new_state);"
        ),
        name="compare_history",
        css_classes=["topology_compare_history", "noselect"],
        is_shortcut=True,
        is_enabled=True,
    )


class CoreDataProvider:
    def __init__(self) -> None:
        self._fake_missing_hosts = False
        self._fake_missing_services = False
        self._core_hosts: dict[HostName, CMCHostObject] = {}
        self._core_services: dict[tuple[HostName, ServiceName], CMCServiceObject] = {}

    def fetch_host_info(self, hostnames: set[HostName]) -> None:
        hostnames = hostnames - set(self._core_hosts)
        if not hostnames:
            return

        # The core is unable to handle big filters
        # Simply fetch everything if too many hosts are queried
        if len(hostnames) > 1000:
            hostname_filter = ""
        else:
            hostname_filter = "\n".join("Filter: name = %s" % lqencode(x) for x in hostnames)
            hostname_filter += "\nOr: %d" % len(hostnames)
        columns = [
            "name",
            "alias",
            "icon_image",
            "address",
            "state",
            "has_been_checked",
            "num_services_warn",
            "num_services_crit",
        ]
        query = f"GET hosts\nColumns: {' '.join(columns)}\n%s" % hostname_filter

        with sites.prepend_site():
            for (
                site,
                hostname,
                alias,
                icon_image,
                address,
                state,
                has_been_checked,
                num_services_warn,
                num_service_crit,
            ) in sites.live().query(query):
                hostnames.remove(hostname)
                self._core_hosts[hostname] = CMCHostObject(
                    site,
                    hostname,
                    state,
                    alias,
                    icon_image,
                    address,
                    has_been_checked,
                    num_services_warn,
                    num_service_crit,
                )

        if self._fake_missing_hosts:
            for hostname in hostnames:
                self._core_hosts[hostname] = CMCHostObject(
                    "fake_site", hostname, 0, "fakehost", None, "127.0.0.1", True, 0, 0
                )

    def fetch_service_info(self, services: set[tuple[HostName, ServiceName]]) -> None:
        services = services - set(self._core_services)
        if not services:
            return

        service_filter = "\n".join(
            (
                (
                    "Filter: host_name = %s\nFilter: description = %s\nAnd: 2"
                    % (lqencode(x), lqencode(y))
                )
                for x, y in services
            )
        )
        service_filter += "\nOr: %d" % len(services)
        columns = [
            "host_name",
            "description",
            "state",
            "icon_image",
        ]
        query = f"GET services\nColumns: {' '.join(columns)}\n%s" % service_filter

        with sites.prepend_site():
            for (
                site,
                hostname,
                description,
                state,
                icon_image,
            ) in sites.live().query(query):
                services.remove((hostname, description))
                self._core_services[(hostname, description)] = CMCServiceObject(
                    site,
                    hostname,
                    description,
                    state,
                    icon_image,
                )

        if self._fake_missing_services:
            for entry in services:
                self._core_services[entry] = CMCServiceObject(
                    "fake_site", entry[0], entry[1], 0, None
                )

    @property
    def core_hosts(self) -> dict[HostName, CMCHostObject]:
        return self._core_hosts

    @property
    def core_services(self) -> dict[tuple[HostName, ServiceName], CMCServiceObject]:
        return self._core_services
