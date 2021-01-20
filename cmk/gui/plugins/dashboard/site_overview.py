#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Optional, NamedTuple, Dict, Any

from cmk.gui import config
import cmk.gui.sites as sites
from cmk.gui.globals import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import Dictionary
from cmk.gui.pages import page_registry, AjaxPage
from cmk.gui.plugins.dashboard import dashlet_registry
from cmk.gui.figures import ABCFigureDashlet, ABCDataGenerator

SiteEntry = NamedTuple("SiteEntry", [
    ("site_id", str),
    ("state", Optional[str]),
    ("link", Optional[str]),
    ("title", str),
    ("num_hosts", Optional[int]),
])


class SiteOverviewDashletDataGenerator(ABCDataGenerator):
    @classmethod
    def vs_parameters(cls):
        return Dictionary(title=_("Properties"), render="form", optional_keys=False, elements=[])

    @classmethod
    def generate_response_data(cls, properties, context, settings):
        return cls._collect_entries()

    @classmethod
    def _collect_entries(cls) -> Dict[str, Any]:
        sites.update_site_states_from_dead_sites()
        entries = []
        for site_id, _sitealias in config.sorted_sites():
            site_spec = config.site(site_id)
            site_status = sites.states().get(site_id, sites.SiteStatus({}))
            state: Optional[str] = site_status.get("state")
            if state is None or state == "disabled":
                link = None
            else:
                link = makeuri_contextless(
                    request,
                    [
                        ("name", "main_single_site"),
                        ("site", site_id),
                    ],
                    filename="dashboard.py",
                )
            entries.append(
                SiteEntry(
                    site_id=site_id,
                    state=state,
                    link=link,
                    title=site_spec["alias"],
                    num_hosts=site_status.get("num_hosts"),
                )._asdict())

        # Debug: Add additional entrie
        reference = entries[0]
        for i in range(10):
            demo_entry = dict(reference)
            demo_entry["site_id"] = "Demo %d" % i
            entries.append(demo_entry)

        return {
            "plot_definitions": [],
            "data": {
                "type": "sites",
                "title": "ABC",
                "sites": entries,
            },
        }


@page_registry.register_page("ajax_site_overview_dashlet_data")
class SitesDashletData(AjaxPage):
    def page(self):
        return SiteOverviewDashletDataGenerator.generate_response_from_request()


@dashlet_registry.register
class SiteOverviewDashlet(ABCFigureDashlet):
    @classmethod
    def type_name(cls):
        return "site_overview"

    @classmethod
    def title(cls):
        return _("Site overview")

    @classmethod
    def description(cls):
        return _("Displays either sites and states or hosts and states of a site")

    @classmethod
    def data_generator(cls):
        return SiteOverviewDashletDataGenerator

    @classmethod
    def single_infos(cls):
        return []

    def show(self):
        self.js_dashlet("ajax_site_overview_dashlet_data.py")
